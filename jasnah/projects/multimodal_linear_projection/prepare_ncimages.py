import base64
import io
import json
from pathlib import Path

import datasets
import numpy as np
from PIL import Image
from tqdm import tqdm

import jasnah
import jasnah.dataset


class Reader:
    PREFIX = "data:image/jpeg;base64,"

    def __init__(self, path: Path):
        self.path = path
        self.file = open(path, "r")

    def __iter__(self):
        return self

    def __next__(self):
        line1 = self.file.readline()
        if not line1:
            raise StopIteration
        line2 = self.file.readline()
        self.file.readline()
        self.file.readline()

        assert line1.startswith(Reader.PREFIX), line1[:100]
        line1 = line1[len(Reader.PREFIX) :].strip(" \n")
        image = base64.b64decode(line1)

        content = json.loads(line2)
        return image, content


def main():
    path = jasnah.dataset.get_dataset("ncimages_ru/raw/v0")

    ds = {"image": [], "content": [], "kind": []}

    for i, (image, content) in tqdm(enumerate(Reader(path / "ncimages" / "part1.txt"))):
        bytes = io.BytesIO(image)
        image = Image.open(bytes).convert("RGB")
        image = np.array(image)

        kind = "leading" if "leading" in content else "description"

        ds["image"].append(image)
        ds["content"].append(content)
        ds["kind"].append(kind)

        if i == 100:
            break

    datasets.Dataset.from_dict(ds).save_to_disk(str(path / "processed"))


if __name__ == "__main__":
    main()
