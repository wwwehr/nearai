import datasets

import jasnah
import jasnah.model

from multimodal import (
    AutoTokenizer,
    ImageTokenizer,
    LlamaMultimodalModel,
    MultimodalTokenizer,
)


def main():
    model_path = jasnah.model.get_model("llama-3-8b-instruct")
    dataset_path = "/home/setup/.jasnah/datasets/ncimages_ru/raw/v0/processed"

    text_tokenizer = AutoTokenizer.from_pretrained(model_path)
    image_tokenizer = ImageTokenizer()
    tokenizer = MultimodalTokenizer(text_tokenizer, image_tokenizer)

    model = LlamaMultimodalModel.from_pretrained(model_path)
    model.train()
    for param in model.model.parameters():
        param.requires_grad = False

    ds = datasets.Dataset.load_from_disk(dataset_path)
    ds = ds.filter(lambda x: x["kind"] == "description")
    split = ds.train_test_split(test_size=0.1)

    train_ds = split["train"]
    test_ds = split["test"]

    print(train_ds[0])


if __name__ == "__main__":
    main()
