import io
from typing import Optional

import datasets
import httpx
import pandas as pd
import PIL
import torch.nn
from multimodal_clip import (
    AutoTokenizer,
    ImageDescription,
    ImageTokenizer,
    LlamaMultimodalModel,
    MultimodalTokenizer,
)
from PIL import Image
from PIL.Image import Image as PILImage
from tensorboardX import SummaryWriter

import jasnah
import jasnah.model

timestamp = jasnah.timestamp()

writer = SummaryWriter(f"logdir/{timestamp}")


def log(name, value, step):
    print(f"{step}: {name} = {value}")
    writer.add_scalar(name, value, step)


def print_params_stats(params: torch.Tensor, prefix: str, step):
    log(f"{prefix}_norm1", params.abs().sum(), step)
    log(f"{prefix}_norm2", (params**2).sum().sqrt(), step)


def print_stats(model: LlamaMultimodalModel, step):
    linear = model.image_projection
    print_params_stats(linear.weight, "weight/", step)
    print_params_stats(linear.bias, "bias/", step)
    if linear.weight.grad is not None:
        print_params_stats(linear.weight.grad, "weight/grad", step)
        print_params_stats(linear.bias.grad, "bias/grad", step)


def get_image(datum) -> Optional[PILImage]:
    try:
        response = httpx.get(datum["URL"])
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGB")
    except Exception as e:
        print(f"Failed to download image {datum['URL']}: {e}")
        return None


def main():
    model_path = jasnah.model.get_model("llama-3-8b-instruct")
    text_tokenizer = AutoTokenizer.from_pretrained(model_path)
    image_tokenizer = ImageTokenizer()
    tokenizer = MultimodalTokenizer(text_tokenizer, image_tokenizer)

    model = LlamaMultimodalModel.from_pretrained(model_path)
    model.train()
    for param in model.model.parameters():
        param.requires_grad = False
    for param in model.lm_head.parameters():
        param.requires_grad = False

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    # dataset_path = "/home/setup/.jasnah/datasets/ncimages_ru/raw/v0/processed"
    # ds = datasets.Dataset.load_from_disk(dataset_path)
    # ds = ds.filter(lambda x: x == "description", input_columns=["kind"])
    df = pd.read_parquet(
        "/workspace/laion400m-meta/part-00000-5b54c5d5-bbcf-484d-a2ce-0d6f73df1a36-c000.snappy.parquet"
    )
    ds = datasets.Dataset.from_pandas(df)
    split = ds.train_test_split(test_size=0.1)
    train_ds = split["train"]
    test_ds = split["test"]

    BATCH_SIZE = 1

    n = len(train_ds)
    bad_offset = 0
    for batch_id in range(0, n, BATCH_SIZE):
        sequences = []
        for i in range(BATCH_SIZE):
            x = train_ds[batch_id + i + bad_offset]
            img = get_image(x)
            while img is None:
                bad_offset += 1
                x = train_ds[batch_id + i + bad_offset]
                img = get_image(x)

            sequences.append(
                [
                    "Опишите следующую картинку",
                    ImageDescription(pil_image=img),
                    x["TEXT"],
                ]
            )

        model_input = tokenizer.encode(sequences, include_labels=True)

        # print("batch id:", batch_id)
        # print("context length:", model_input["n_ctx"])
        log("context_length", model_input["n_ctx"], batch_id)

        labels = model_input.pop("labels")
        weights = model_input.pop("weights")

        optimizer.zero_grad()
        outputs = model(**model_input)

        logits = outputs.logits

        loss = torch.nn.functional.cross_entropy(logits.permute(0, 2, 1), labels, reduction="none")

        loss = ((loss * weights).sum(1) / weights.sum(1)).mean()
        loss.backward()

        optimizer.step()

        log("loss", loss.item(), batch_id)
        print_stats(model, batch_id)


if __name__ == "__main__":
    main()
