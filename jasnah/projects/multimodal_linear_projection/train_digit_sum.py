import os
import random

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from tqdm import tqdm

import jasnah
import jasnah.model

from .multimodal import ImageTokenizer, LlamaMultimodalModel, MultimodalTokenizer, encode_only
from .train import summary


class CharLevelTokenizer:
    def __call__(self, text):
        return self.encode(text)

    def encode(self, text):
        return {"input_ids": [ord(c) for c in text]}


def prepare_data():
    rng = random.Random(0)
    data = []
    for _ in range(32 * 1024):
        a = rng.randint(0, 1000)
        b = rng.randint(0, 1000)
        c = a + b
        data.append(f"{a} + {b} = {c}")

    return data


def prepare_row(row):
    prefix, suffix = row.split(" = ")
    return [encode_only(prefix + " = "), suffix]


def prepare_batch(batch):
    return [prepare_row(row) for row in batch]


def train(data):
    total_ranks = int(os.getenv("WORLD_SIZE"))
    local_rank = int(os.getenv("LOCAL_RANK"))

    device = torch.device("cuda", local_rank)

    model_path = jasnah.model.get_model("llama-3-8b")
    model = LlamaMultimodalModel.from_pretrained(model_path).to(device)

    model.train()
    model.freeze_lang_model()
    model.lm_head.requires_grad_(True)

    model = DDP(model, device_ids=[local_rank], output_device=local_rank)

    summary(model, print_params=False)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-5)
    tokenizer = MultimodalTokenizer(CharLevelTokenizer(), ImageTokenizer())

    EPOCHS = 10
    BATCH_SIZE = 8 * 128

    assert BATCH_SIZE % total_ranks == 0
    assert len(data) % BATCH_SIZE == 0

    BATCH_SIZE_PER_RANK = BATCH_SIZE // total_ranks
    pbar = tqdm(total=len(data) * EPOCHS)

    running_loss = None

    for epoch in range(EPOCHS):
        for i in range(0, len(data), BATCH_SIZE):
            batch = data[i + BATCH_SIZE_PER_RANK * local_rank : i + BATCH_SIZE_PER_RANK * (local_rank + 1)]
            model_input = tokenizer.encode(batch, include_labels=True)

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

            loss_x = loss.item()
            if running_loss is None:
                running_loss = loss_x
            running_loss = 0.9 * running_loss + 0.1 * loss_x

            pbar.update(BATCH_SIZE)
            pbar.set_description(f"{epoch} {i} loss={loss_x:.3f} wloss={running_loss:.3f}")


def main():
    dist.init_process_group("nccl")
    data = prepare_data()
    train(data)


if __name__ == "__main__":
    main()
