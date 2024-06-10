import base64
import json
import tarfile
from itertools import product
from pathlib import Path
from typing import List, Tuple

import datasets
from PIL import Image

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

        return LazyItem(line1, line2)


class LazyItem:
    def __init__(self, image: str, content: str):
        self._image_raw = image
        self._content_raw = content
        self._image = None
        self._content = None

    @property
    def content(self) -> dict:
        if self._content is None:
            self._content = json.loads(self._content_raw)
        return self._content

    @property
    def image(self) -> Image.Image:
        if self._image is None:
            assert self._image_raw.startswith(Reader.PREFIX), self._image_raw
            line = self._image_raw[len(Reader.PREFIX) :].strip(" \n")
            image = base64.b64decode(line)
            self._image = {"path": None, "bytes": image}
        return self._image


def generate_descriptions(input: List[Tuple[Path, int]], mod: int):
    for file, target_idx in input:
        reader = Reader(file)
        for idx, item in enumerate(reader):
            if idx % mod != target_idx:
                continue

            if "descr" not in item.content:
                continue

            boxes = [{"x": box["x"], "y": box["y"], "description": box["descr"]} for box in item.content["boxes"]]
            yield {"image": item.image, "description": item.content["descr"], "boxes": boxes}


def generate_leading(input: List[Tuple[Path, int]], mod: int):
    for file, target_idx in input:
        reader = Reader(file)
        for idx, item in enumerate(reader):
            if idx % mod != target_idx:
                continue

            if "main" not in item.content:
                continue

            yield dict(image=item.image, **item.content)


def main():
    NUM_PROCESS = 120
    SUFFIX = ""

    path = jasnah.dataset.get_dataset("ncimages_ru_raw")
    uncompressed = path / "uncompressed"

    processed = path / "processed"
    processed.mkdir(exist_ok=True, parents=True)

    if not uncompressed.exists():
        with tarfile.open(path / "ncimages.tar.gz") as f:
            f.extractall(uncompressed)

    raw_dataset_path = uncompressed / "ncimages"

    files = list(raw_dataset_path.glob("part*.txt"))
    input = list(product(files, range(NUM_PROCESS)))

    ds_description = datasets.Dataset.from_generator(
        generate_descriptions,
        gen_kwargs={"input": input, "mod": NUM_PROCESS},
        features=datasets.Features(
            {
                "image": datasets.Image(),
                "description": datasets.Value("string"),
                "boxes": [
                    {
                        "description": datasets.Value("string"),
                        "x": datasets.Value("float"),
                        "y": datasets.Value("float"),
                    }
                ],
            }
        ),
        num_proc=NUM_PROCESS,
    )

    ds_description.save_to_disk(str(processed / f"descriptions{SUFFIX}"))

    question_type = {
        "question": datasets.Value("string"),
        "arrows": [{"x": datasets.Value("float"), "y": datasets.Value("float")}],
        "answer_type": datasets.Value("int8"),
        "answer": datasets.Value("string"),
    }
    features = datasets.Features({"image": datasets.Image(), "main": question_type, "leading": [question_type]})
    ds_leading = datasets.Dataset.from_generator(
        generate_leading,
        gen_kwargs={"input": input, "mod": NUM_PROCESS},
        features=features,
        num_proc=NUM_PROCESS,
    )

    ds_leading.save_to_disk(str(processed / f"leading{SUFFIX}"))


if __name__ == "__main__":
    main()
