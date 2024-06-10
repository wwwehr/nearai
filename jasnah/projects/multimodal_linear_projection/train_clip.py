import io
from pathlib import Path
from typing import Optional

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

import datasets
import jasnah
import jasnah.model

timestamp = jasnah.timestamp()

# writer_path = f"logdir/{timestamp}"
writer_path = f"logdir/devrun_1"
writer = SummaryWriter(writer_path)
client = httpx.Client(follow_redirects=True)


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
        response = client.get(datum["URL"], timeout=3)
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

    checkpoints = Path("./logdir/devrun_1").glob("projection-*.pt")
    checkpoints = sorted(checkpoints, key=lambda x: int(x.stem.split("-")[1]))
    latest_checkpoint = checkpoints[-1] if checkpoints else None
    print(f"latest_checkpoint: {latest_checkpoint}")
    starting_index = 0
    if latest_checkpoint:
        model.load_projection(latest_checkpoint)
        starting_index = int(latest_checkpoint.stem.split("-")[1])

    model.train()
    for param in model.model.parameters():
        param.requires_grad = False
    for param in model.lm_head.parameters():
        param.requires_grad = False
    model.to("cuda")

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    df = pd.read_parquet(
        "/workspace/laion400m-meta/part-00000-5b54c5d5-bbcf-484d-a2ce-0d6f73df1a36-c000.snappy.parquet"
    )
    ds = datasets.Dataset.from_pandas(df)
    split = ds.train_test_split(test_size=0.1)
    train_ds = split["train"]
    test_ds = split["test"]

    BATCH_SIZE = 1

    n = len(train_ds)
    for batch_id in range(starting_index, n, BATCH_SIZE):
        if batch_id % 1000 == 0 and batch_id > 0:
            model.save_projection(f"{writer_path}/projection-{batch_id}.pt")

        try:
            sequences = []
            for i in range(BATCH_SIZE):
                x = train_ds[batch_id + i]
                img = get_image(x)
                if img is None:
                    break
                sequences.append(
                    [
                        "Please describe the following image: \n\n",
                        ImageDescription(pil_image=img),
                        x["TEXT"],
                    ]
                )
            if not sequences:
                continue

            model_input = tokenizer.encode(sequences, include_labels=True)

            # print("batch id:", batch_id)
            # print("context length:", model_input["n_ctx"])
            log("context_length", model_input["n_ctx"], batch_id)

            labels = model_input.pop("labels")
            weights = model_input.pop("weights")

            optimizer.zero_grad()
            outputs = model(**model_input)

            logits = outputs.logits

            loss = torch.nn.functional.cross_entropy(
                logits.permute(0, 2, 1), labels, reduction="none"
            )

            loss = ((loss * weights).sum(1) / weights.sum(1)).mean()
            loss.backward()

            optimizer.step()

            log("loss", loss.item(), batch_id)
            print_stats(model, batch_id)
        except Exception as e:
            print(f"Failed to process batch {batch_id}: {e}")


if __name__ == "__main__":
    main()
