import concurrent.futures
import io
import os
from pathlib import Path

import httpx
import pandas as pd
import torch.distributed as dist
import torch.nn
from multimodal_clip import (
    AutoTokenizer,
    ImageDescription,
    ImageTokenizer,
    LlamaMultimodalModel,
    MultimodalTokenizer,
)
from PIL import Image
from tensorboardX import SummaryWriter
from torch.nn.parallel import DistributedDataParallel as DDP
from tqdm import tqdm

import datasets
import jasnah
import jasnah.model

client = httpx.Client(follow_redirects=True)


TOTAL_RANKS = int(os.getenv("WORLD_SIZE"))
LOCAL_RANK = int(os.getenv("LOCAL_RANK"))
print(f"LOCAL_RANK: {LOCAL_RANK}, TOTAL_RANKS: {TOTAL_RANKS}")

CHECKPOINT_START = 1000
CHECKPOINT_INC = 2
CHECKPOINT_TOP = 180000
CHECKPOINT_EVERY = 2000
STATS_EVERY = 100

timestamp = jasnah.timestamp()
writer_path = f"logdir/devrun_2"
if LOCAL_RANK == 0:
    writer = SummaryWriter(writer_path)

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

    # folder = Path("checkpoints") / timestamp
    folder = Path(writer_path)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"model_{samples}.pt"
    torch.save(model.image_projection.state_dict(), path)


def load_checkpoint(model: LlamaMultimodalModel):
    folder = Path(writer_path)
    checkpoints = folder.glob("model_*.pt")
    checkpoints = sorted(checkpoints, key=lambda x: int(x.stem.split("_")[1]))
    latest_checkpoint = checkpoints[-1] if checkpoints else None
    assert latest_checkpoint, "No checkpoints found"
    model.load_projection(latest_checkpoint)
    print("Loaded checkpoint", latest_checkpoint)
    return int(latest_checkpoint.stem.split("_")[1])


def get_image(datum):
    try:
        response = client.get(datum["URL"], timeout=3)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        ## sanity checks on size
        assert image.height > 10
        assert image.width > 10
        return image
    except Exception as e:
        print(f"Failed to download image {datum['URL']}: {e}")
        return None


def main():

    device = torch.device("cuda", LOCAL_RANK)

    model_path = jasnah.model.get_model("llama-3-8b-instruct")
    model = LlamaMultimodalModel.from_pretrained(model_path).to(device)

    init_batch = load_checkpoint(model)
    # init_batches = 0

    model.train()
    model.freeze_lang_model()
    summary(model)

    model = DDP(model, device_ids=[LOCAL_RANK], output_device=LOCAL_RANK)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    text_tokenizer = AutoTokenizer.from_pretrained(model_path)
    image_tokenizer = ImageTokenizer()
    tokenizer = MultimodalTokenizer(text_tokenizer, image_tokenizer)

    # dataset_path = "/home/setup/.jasnah/registry/datasets/ncimages_ru/raw/v0/processed/descriptions"
    # ds = datasets.Dataset.load_from_disk(dataset_path)
    df = pd.read_parquet(
        "/workspace/laion400m-meta/part-00000-5b54c5d5-bbcf-484d-a2ce-0d6f73df1a36-c000.snappy.parquet"
    )
    ds = datasets.Dataset.from_pandas(df)

    split = ds.train_test_split(test_size=0.1, seed=SEED)
    train_ds = split["train"]
    test_ds = split["test"]

    EPOCHS = 1
    BATCH_SIZE = 4 * 6

    assert BATCH_SIZE % TOTAL_RANKS == 0

    BATCH_SIZE_PER_RANK = BATCH_SIZE // TOTAL_RANKS

    n = len(train_ds)
    pbar = tqdm(total=len(train_ds) * EPOCHS, initial=init_batch)

    checkpoint(model.module, 0)
    next_checkpoint = init_batch
    next_stat = 0

    for epoch in range(EPOCHS):
        for batch_id in range(init_batch, n, BATCH_SIZE):
            batch_from = batch_id + BATCH_SIZE_PER_RANK * LOCAL_RANK
            batch_to = batch_from + BATCH_SIZE_PER_RANK

            with concurrent.futures.ThreadPoolExecutor() as executor:
                # run get_image in a separate thread for batch
                futures = [
                    executor.submit(get_image, train_ds[batch_id + i])
                    for i in range(batch_from, batch_to)
                ]
                images = [future.result() for future in futures]

            sequences = []
            # TODO: Can we implement prefetching?
            for i, img in zip(range(batch_from, batch_to), images):
                x = train_ds[batch_id + i]
                if img is None or x["TEXT"] is None or x["TEXT"] == "":
                    continue
                sequences.append(
                    [
                        "Please describe the following image:\n\n",
                        ImageDescription(pil_image=img),
                        x["TEXT"],
                    ]
                )
            if not sequences:
                continue

            # sequences = []
            # # TODO: Can we implement prefetching?
            # for i in range(batch_from, batch_to):
            #     x = train_ds[batch_id + i]
            #     sequences.append(
            #         [
            #             "Опишите следующую картинку",
            #             ImageDescription(pil_image=x["image"]),
            #             x["description"],
            #         ]
            #     )

            try:
                model_input = tokenizer.encode(sequences, include_labels=True, context_size=512)
            except AssertionError:
                # TODO: This will get nodes out of sync with regard to batch id
                continue

            # TODO: Can we avoid reallocating input tensors every time?
            model_input = {
                key: value.to(device) if key != "n_ctx" else value
                for key, value in model_input.items()
            }

            labels: torch.Tensor = model_input.pop("labels")
            weights: torch.Tensor = model_input.pop("weights")

            optimizer.zero_grad()
            outputs = model(**model_input)

            logits: torch.Tensor = outputs.logits

            loss = torch.nn.functional.cross_entropy(
                logits.permute(0, 2, 1), labels, reduction="none"
            )

            loss = ((loss * weights).sum(1) / weights.sum(1)).mean()
            loss.backward()

            optimizer.step()

            log("loss", loss.item(), batch_id)
            pbar.update(BATCH_SIZE)

            if batch_id > next_stat:
                print_stats(model.module, batch_id)
                next_stat = batch_id + STATS_EVERY

            if batch_id > next_checkpoint:
                checkpoint(model.module, batch_id)
                ## next checkpoint should be at least 2 *
                next_checkpoint += CHECKPOINT_EVERY


if __name__ == "__main__":
    dist.init_process_group("nccl")
    main()
