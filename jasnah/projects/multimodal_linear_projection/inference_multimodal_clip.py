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

checkpoints = Path("./logdir/devrun_1").glob("projection-*.pt")
checkpoints = sorted(checkpoints, key=lambda x: int(x.stem.split("-")[1]))
latest_checkpoint = checkpoints[-1] if checkpoints else None
print(f"latest_checkpoint: {latest_checkpoint}")
starting_index = 0
if latest_checkpoint:
    model.load_projection(latest_checkpoint)
    starting_index = int(latest_checkpoint.stem.split("-")[1])

## prompt with or without
prompt = [
    [
        "Please describe this image:\n\n",
        ImageDescription(
            pil_image=Image.open("./big-ship.jpg").convert("RGB"),
        ),
        "\n\n",
        "Analysis:",
        "\n",
    ]
]
for i in range(32):

    ## Sample next token
    model_input = tokenizer.encode(prompt)
    model_outputs = model(**model_input)
    last_model_outputs = model_outputs.logits[:, -1, :].flatten()
    new_token = torch.argmax(last_model_outputs).item()
    new_token_value = text_tokenizer.decode(new_token)
    prompt[0][-1] += new_token_value

    print(new_token_value, end="")
