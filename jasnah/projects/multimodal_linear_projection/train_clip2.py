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
from PIL import Image, PngImagePlugin
from tensorboardX import SummaryWriter
from torch.nn.parallel import DistributedDataParallel as DDP
from tqdm import tqdm

import datasets
import jasnah
import jasnah.model

PngImagePlugin.MAX_TEXT_CHUNK = 100 * (1024**2)
TOTAL_RANKS = int(os.getenv("WORLD_SIZE"))
LOCAL_RANK = int(os.getenv("LOCAL_RANK"))
print(f"LOCAL_RANK: {LOCAL_RANK} / {TOTAL_RANKS}")

CHECKPOINT_START = 1000
CHECKPOINT_INC = 2
CHECKPOINT_TOP = 180000
CHECKPOINT_EVERY = 2000
STATS_EVERY = 500

timestamp = jasnah.timestamp()
writer_path = f"logdir/devrun_1_russian"
if LOCAL_RANK == 0:
    writer = SummaryWriter(writer_path)

SEED = 42


def log(name, value, step):
    if LOCAL_RANK == 0:
        if isinstance(value, torch.Tensor) and value.dtype == torch.bfloat16:
            value = value.to(torch.float32)

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
    try:
        assert latest_checkpoint, "No checkpoints found"
    except AssertionError as e:
        print(e)
        return 0
    model.load_projection(latest_checkpoint)
    print("Loaded checkpoint", latest_checkpoint)
    return int(latest_checkpoint.stem.split("_")[1])


def main():

    device = torch.device("cuda", LOCAL_RANK)

    model_path = jasnah.model.get_model("llama-3-8b-instruct")
    model = LlamaMultimodalModel.from_pretrained(model_path).to(device)
    model.init_clip(device)

    init_batch = load_checkpoint(model)

    model.to(torch.bfloat16)
    model.train()
    model.freeze_lang_model()
    summary(model)

    model = DDP(model, device_ids=[LOCAL_RANK], output_device=LOCAL_RANK)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    text_tokenizer = AutoTokenizer.from_pretrained(model_path)
    image_tokenizer = ImageTokenizer()
    tokenizer = MultimodalTokenizer(text_tokenizer, image_tokenizer)

    dataset_path = "/home/user/.jasnah/datasets/ncimages_ru/raw/v0/processed/descriptions"
    ds = datasets.Dataset.load_from_disk(dataset_path)
    # dataset_path = "~/.jasnah/datasets/laion400m_metadata/processed/descriptions"
    # ds = datasets.Dataset.load_from_disk(dataset_path)

    split = ds.train_test_split(test_size=0.01, seed=SEED)
    train_ds = split["train"]
    test_ds = split["test"]

    EPOCHS = 1
    BATCH_SIZE_PER_RANK = 4
    BATCH_SIZE = BATCH_SIZE_PER_RANK * TOTAL_RANKS
    assert BATCH_SIZE % TOTAL_RANKS == 0

    BATCH_SIZE_PER_RANK = BATCH_SIZE // TOTAL_RANKS

    n = len(train_ds)
    pbar = tqdm(total=len(train_ds) * EPOCHS, initial=init_batch)

    checkpoint(model.module, 0)
    next_checkpoint = init_batch
    next_stat = 0

    print("Starting training from batch ", init_batch)
    for epoch in range(EPOCHS):
        for batch_id in range(init_batch, n, BATCH_SIZE):
            batch_from = batch_id + BATCH_SIZE_PER_RANK * LOCAL_RANK
            batch_to = batch_from + BATCH_SIZE_PER_RANK

            sequences = []
            # TODO: Can we implement prefetching?
            for i in range(batch_from, batch_to):
                x = train_ds[batch_id + i]
                sequences.append(
                    [
                        "Опишите следующую картинку",
                        ImageDescription(pil_image=x["image"].convert("RGB")),
                        x["description"],
                    ]
                )

            # sequences = []
            # for i in range(batch_from, batch_to):
            #     x = train_ds[batch_id + i]
            #     sequences.append(
            #         [
            #             "Please describe the following image:\n\n",
            #             ImageDescription(pil_image=x["image"].convert("RGB")),
            #             str(x["description"]),
            #         ]
            #     )

            try:
                model_input = tokenizer.encode(sequences, include_labels=True, context_size=512)
            except AssertionError:
                # TODO: This will get nodes out of sync with regard to batch id
                continue

            # TODO: Can we avoid reallocating input tensors every time?
            model_input["patches"] = model_input["patches"].to(torch.bfloat16)
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
