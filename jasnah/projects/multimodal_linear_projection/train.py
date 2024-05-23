import datasets
import torch.nn
from multimodal import (
    AutoTokenizer,
    ImageDescription,
    ImageTokenizer,
    LlamaMultimodalModel,
    MultimodalTokenizer,
)
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


def main():
    model_path = jasnah.model.get_model("llama-3-8b-instruct")
    text_tokenizer = AutoTokenizer.from_pretrained(model_path)
    image_tokenizer = ImageTokenizer()
    tokenizer = MultimodalTokenizer(text_tokenizer, image_tokenizer)

    model = LlamaMultimodalModel.from_pretrained(model_path)
    model.train()
    for param in model.model.parameters():
        param.requires_grad = False

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    dataset_path = "/home/setup/.jasnah/datasets/ncimages_ru/raw/v0/processed"
    ds = datasets.Dataset.load_from_disk(dataset_path)
    ds = ds.filter(lambda x: x == "description", input_columns=["kind"])
    split = ds.train_test_split(test_size=0.1)
    train_ds = split["train"]
    test_ds = split["test"]

    BATCH_SIZE = 1

    n = len(train_ds)
    for batch_id in range(0, n, BATCH_SIZE):
        sequences = []
        for i in range(BATCH_SIZE):
            x = train_ds[batch_id + i]
            sequences.append(
                [
                    "Опишите следующую картинку",
                    ImageDescription(pil_image=x["image"]),
                    x["content"]["descr"],
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

        loss = torch.nn.functional.cross_entropy(
            logits.permute(0, 2, 1), labels, reduction="none"
        )

        loss = ((loss * weights).sum(1) / weights.sum(1)).mean()
        loss.backward()

        optimizer.step()

        log("loss", loss.item(), batch_id)
        print_stats(model, batch_id)


if __name__ == "__main__":
    main()
