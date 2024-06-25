import os
import shutil
from functools import partial
from itertools import count
from pathlib import Path
from typing import Optional

import datasets
import PIL.Image
import requests
import torch.distributed as dist
import torch.nn
from tensorboardX import SummaryWriter
from torch.nn.parallel import DistributedDataParallel as DDP
from tqdm import tqdm

import jasnah
import jasnah.dataset
import jasnah.model

from .multimodal import AutoTokenizer, ImageDescription, ImageTokenizer, LlamaMultimodalModel, MultimodalTokenizer

TOTAL_RANKS = int(os.getenv("WORLD_SIZE"))
LOCAL_RANK = int(os.getenv("LOCAL_RANK"))

CHECKPOINT_START = 1000
CHECKPOINT_INC = 2
CHECKPOINT_TOP = 180000
STATS_EVERY = 500

if LOCAL_RANK == 0:
    timestamp = jasnah.timestamp()
    writer = SummaryWriter(f"logdir/laion/{timestamp}")

SEED = 42


def log(name, value, step):
    if LOCAL_RANK == 0:
        # print(f"{step}: {name} = {value}")
        writer.add_scalar(name, value, step)


def print_params_stats(params: torch.Tensor, prefix: str, step):
    log(f"{prefix}_norm1", params.abs().mean(), step)
    log(f"{prefix}_norm2", (params**2).mean().sqrt(), step)


def print_stats(model: LlamaMultimodalModel, step):
    linear = model.image_projection
    print_params_stats(linear.weight, "weight/", step)
    print_params_stats(linear.bias, "bias/", step)
    if linear.weight.grad is not None:
        print_params_stats(linear.weight.grad, "weight/grad", step)
        print_params_stats(linear.bias.grad, "bias/grad", step)


def summary(model: torch.nn.Module, print_params=True):
    trainable_params = 0
    for name, param in model.named_parameters():
        if param.requires_grad:
            if print_params:
                print(name, param.size())
            trainable_params += param.numel()
    print("Trainable params:", trainable_params)


def checkpoint(model: LlamaMultimodalModel, samples: int):
    if LOCAL_RANK != 0:
        return

    folder = Path("checkpoints") / timestamp
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"model_{samples}.pt"
    torch.save(model.image_projection.state_dict(), path)


CACHE = Path("image_cache")
CACHE.mkdir(exist_ok=True)


def to_generator(ds: datasets.Dataset):
    for row in ds:
        yield row


def download_image(row):
    id = str(row["SAMPLE_ID"])
    image_url = row["URL"]

    path = CACHE / f"{id}"
    path_no = CACHE / f"{id}.no"

    row["IMAGE"] = None

    try:
        if path_no.exists():
            if path.exists():
                _ = PIL.Image.open(path)
                row["IMAGE"] = path
            return row
        path_no.touch()

        response = requests.get(image_url, stream=True, timeout=1)

        if response.status_code != 200:
            return row

        with open(path, "wb") as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)

        _ = PIL.Image.open(path)
        row["IMAGE"] = path
    except:
        pass

    return row


def transpose(batch):
    """
    Convert from dictionary of lists to lists of dictionaries

    input: {a: [1, 2, 3], b: [4, 5, 6]}
    output: [{a: 1, b: 4}, {a: 2, b: 5}, {a: 3, b: 6}]
    """
    keys = list(batch.keys())
    batch_size = len(batch[keys[0]])
    return [{key: batch[key][i] for key in keys} for i in range(batch_size)]


def main():
    ds_raw = jasnah.dataset.load_dataset("laion400m_metadata")
    ds = datasets.IterableDataset.from_generator(partial(to_generator, ds_raw))
    ds = ds.map(download_image).filter(lambda x: x["IMAGE"] != None)

    device = torch.device("cuda", LOCAL_RANK)

    model_path = jasnah.model.get_model("llama-3-8b-instruct")
    model = LlamaMultimodalModel.from_pretrained(model_path).to(device)

    model.train()
    model.freeze_lang_model()
    summary(model)

    model = DDP(model, device_ids=[LOCAL_RANK], output_device=LOCAL_RANK)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    text_tokenizer = AutoTokenizer.from_pretrained(model_path)
    image_tokenizer = ImageTokenizer()
    tokenizer = MultimodalTokenizer(text_tokenizer, image_tokenizer)

    EPOCHS = 1
    BATCH_SIZE = 8 * 4

    assert BATCH_SIZE % TOTAL_RANKS == 0

    BATCH_SIZE_PER_RANK = BATCH_SIZE // TOTAL_RANKS
    pbar = tqdm()

    checkpoint(model.module, 0)
    next_checkpoint = CHECKPOINT_START
    next_stat = 0

    for epoch in range(EPOCHS):
        for ix, batch in enumerate(ds.iter(batch_size=BATCH_SIZE)):

            batch_from = BATCH_SIZE_PER_RANK * LOCAL_RANK
            batch_to = batch_from + BATCH_SIZE_PER_RANK
            batch = transpose(batch)

            sequences = []
            # TODO: Can we implement prefetching?
            for i in range(batch_from, batch_to):
                x = batch[i]
                image = PIL.Image.open(x["IMAGE"])
                sequences.append(
                    [
                        "Describe the image in one sentence, focusing on the most prominent elements:",
                        ImageDescription(pil_image=image),
                        x["TEXT"],
                    ]
                )

            try:
                model_input = tokenizer.encode(sequences, include_labels=True, context_size=512)
            except Exception as e:
                print("Found error while encoding sequences.")
                print(e)
                # TODO: This will get nodes out of sync with regard to batch id
                continue

            # TODO: Can we avoid reallocating input tensors every time?
            model_input = {key: value.to(device) if key != "n_ctx" else value for key, value in model_input.items()}

            labels: torch.Tensor = model_input.pop("labels")
            weights: torch.Tensor = model_input.pop("weights")

            optimizer.zero_grad()
            outputs = model(**model_input)

            logits: torch.Tensor = outputs.logits

            loss = torch.nn.functional.cross_entropy(logits.permute(0, 2, 1), labels, reduction="none")

            loss = ((loss * weights).sum(1) / weights.sum(1)).mean()
            loss.backward()

            optimizer.step()

            batch_id = (ix + 1) * BATCH_SIZE

            log("loss", loss.item(), batch_id)
            pbar.update(BATCH_SIZE)

            if batch_id > next_stat:
                print_stats(model.module, batch_id)
                next_stat = batch_id + STATS_EVERY

            if batch_id > next_checkpoint:
                checkpoint(model.module, batch_id)
                next_checkpoint = min(next_checkpoint * CHECKPOINT_INC, next_checkpoint + CHECKPOINT_TOP)


if __name__ == "__main__":
    if TOTAL_RANKS > 1:
        dist.init_process_group("nccl")

    main()
