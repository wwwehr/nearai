import io
from pathlib import Path
from typing import Optional

import httpx
import pandas as pd
import PIL
import torch.nn
from multimodal_clip import (AutoTokenizer, ImageDescription, ImageTokenizer,
                             LlamaMultimodalModel, MultimodalTokenizer)
from PIL import Image
from PIL.Image import Image as PILImage
from transformers import AutoModelForCausalLM, LlamaConfig, LlamaForCausalLM

import datasets
import jasnah
import jasnah.model

timestamp = jasnah.timestamp()

model_path = jasnah.model.get_model("llama-3-8b-instruct")
text_tokenizer = AutoTokenizer.from_pretrained(model_path)
image_tokenizer = ImageTokenizer()
tokenizer = MultimodalTokenizer(text_tokenizer, image_tokenizer)

model = LlamaMultimodalModel.from_pretrained(model_path)
model.to("cuda")
model.init_clip("cuda")
# model.to(torch.bfloat16)

checkpoint_path = Path("./logdir/devrun_1_russian")
checkpoints = checkpoint_path.glob("*.pt")
checkpoints = sorted(checkpoints, key=lambda x: int(x.stem.split("_")[1]))
latest_checkpoint = checkpoints[-1] if checkpoints else None
print(f"latest_checkpoint: {latest_checkpoint}")
starting_index = 0
if latest_checkpoint:
    # model.load_projection((checkpoint_path / "model_1290016.pt").as_posix())
    model.load_projection(latest_checkpoint)
    starting_index = int(latest_checkpoint.stem.split("_")[1])


def sample_prompt(prompt):
    for i in range(64):

        ## Sample next token
        model_input = tokenizer.encode(prompt)
        # model_input["patches"] = model_input["patches"].to(torch.bfloat16)
        model_outputs = model(**model_input)
        last_model_outputs = model_outputs.logits[:, -1, :].flatten()
        new_token = torch.argmax(last_model_outputs).item()
        new_token_value = text_tokenizer.decode(new_token)
        if new_token_value == text_tokenizer.eos_token:
            break
        prompt[0][-1] += new_token_value

        print(new_token_value, end="")


## prompt with or without
sample_prompt(
    [
        [
            "Опишите следующую картинку:\n",
            ImageDescription(
                pil_image=Image.open("./0.jpg").convert("RGB"),
            ),
            "\n\n",
            "This image shows a",
        ]
    ]
)
