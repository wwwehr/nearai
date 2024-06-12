import json
import shutil
import sys
from pathlib import Path

import datasets
import PIL.Image
import torch
from tqdm import tqdm

import jasnah.model

from .multimodal import AutoTokenizer, ImageDescription, ImageTokenizer, LlamaMultimodalModel, MultimodalTokenizer


def filter_checkpoints(src_folder: Path, target_folder: Path):
    checkpoints = []
    for file in src_folder.glob("*.pt"):
        batch_id = file.name.strip("model_.pt")
        batch_id = int(batch_id)
        checkpoints.append((batch_id, file))

    checkpoints.sort()

    keep = []
    last_block = -1
    for num, file in checkpoints:
        block = num // 100_000
        if num == 0 or block > last_block or len(keep) == 1:
            keep.append(file)
        last_block = block
        keep[-1] = file

    for file in keep:
        shutil.copy2(file, target_folder)


def check_model(image_projection_file: Path):
    model_batch_id = int(image_projection_file.name.strip("model_.pt"))

    ds = datasets.load_from_disk("/home/setup/small_ncimages_ru")

    model_path = jasnah.model.get_model("llama-3-8b-instruct")

    device = torch.device("cuda", 0)
    model: LlamaMultimodalModel = LlamaMultimodalModel.from_pretrained(model_path).to(device)
    model.eval()

    model.image_projection.load_state_dict(torch.load(image_projection_file))

    text_tokenizer = AutoTokenizer.from_pretrained(model_path)
    image_tokenizer = ImageTokenizer()
    tokenizer = MultimodalTokenizer(text_tokenizer, image_tokenizer)

    output_folder = Path("results") / str(model_batch_id)
    output_folder.mkdir(exist_ok=True, parents=True)

    for i, x in tqdm(enumerate(ds)):
        image: PIL.Image.Image = x["image"]
        description = x["description"]

        sequence = [["Опишите следующую картинку", ImageDescription(pil_image=image)]]

        model_input = tokenizer.encode(sequence, include_labels=True, context_size=512)

        tokens = model_input["tokens"].tolist()[0]
        tokens_pos = model_input["tokens_pos"].tolist()[0]

        model_input.pop("labels")
        model_input.pop("weights")
        model_input = {key: value.to(device) if key != "n_ctx" else value for key, value in model_input.items()}

        target = max(tokens_pos)

        generated_description = []

        for delta in (pbar := tqdm(range(32), leave=False)):
            output = model(**model_input)

            n_token = output.logits[0, target + delta].argmax().item()
            tokens.append(n_token)
            tokens_pos.append(target + delta + 1)
            generated_description.append(n_token)

            model_input["tokens"] = torch.tensor([tokens], device=device)
            model_input["tokens_pos"] = torch.tensor([tokens_pos], device=device)

            generated_text = text_tokenizer.decode(generated_description, skip_special_tokens=False)

            pbar.set_description(f"output={generated_text[-10:]}")

        image.save(output_folder / f"image_{i}.jpg")
        generated_text = text_tokenizer.decode(generated_description, skip_special_tokens=False)
        with open(output_folder / f"description_{i}.txt", "w") as f:
            print("Expected:", description, file=f)
            print("Generated:", generated_text, file=f)


def main():
    check_model(Path("/home/setup/dev/jasnah-cli/jasnah/projects/checkpoints/saved/model_1029504.pt"))


if __name__ == "__main__":
    main()
