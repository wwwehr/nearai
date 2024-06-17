import concurrent.futures
import io
import json
import multiprocessing as mp
import warnings
from collections import defaultdict
from itertools import islice, product
from pathlib import Path
from typing import Iterator, List, Tuple

import httpx
from PIL import Image, PngImagePlugin
from tqdm import tqdm

import datasets
import jasnah
import jasnah.dataset

LARGE_ENOUGH_NUMBER = 100
PngImagePlugin.MAX_TEXT_CHUNK = LARGE_ENOUGH_NUMBER * (1024**2)

warnings.filterwarnings("ignore")

MAX_CONCURRENT = 128
NUM_PROCESS = 128

headers = {
    "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
}


def fetch_image(datum):
    try:
        with httpx.Client() as client:
            response = client.get(datum["URL"], timeout=5, headers=headers, follow_redirects=True)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content)).convert("RGB")

            ## sanity checks on size / format
            assert image.mode == "RGB"
            assert image.height > 10
            assert image.width > 10
            assert image.height < 4096
            assert image.width < 4096

            ## Catch any zip bombs
            img_bytes = io.BytesIO()
            image.save(img_bytes, format="PNG")
            loaded_image = Image.open(img_bytes)

            return (loaded_image, datum)
    except Exception as e:
        return None


def generate_descriptions(input: datasets.Dataset, samples: int, pos: int):
    input: datasets.Dataset = input[0]
    samples: int = samples[0]
    samples = samples[1] - samples[0]
    pos: int = pos[0]

    remaining = samples
    ds = input.select(range(pos, len(input), NUM_PROCESS))
    with concurrent.futures.ThreadPoolExecutor() as executor:
        tasks = iter(executor.submit(fetch_image, datum=datum) for datum in ds)
        futures = list(islice(tasks, MAX_CONCURRENT))
        while futures:
            completed, ongoing_futures = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED
            )
            futures = list(ongoing_futures)
            for completed_future in completed:

                result = completed_future.result()
                if result is not None:
                    remaining -= 1
                    image, datum = result
                    yield {
                        "image": image,
                        "description": datum["TEXT"],
                    }

                try:
                    if remaining > 0:
                        next_task = next(tasks)
                        futures.append(next_task)
                    else:
                        return
                except StopIteration:
                    continue


def chunkify(n, num_chunks):
    """Split n into num_chunks chunks. Any remainder is split evenly among the chunks."""
    chunk_size = n // num_chunks
    remainder = n % num_chunks
    start = 0
    for i in range(num_chunks):
        end = start + chunk_size + (1 if i < remainder else 0)
        yield start, end
        start = end


def main():
    SUFFIX = ""

    n = 3_000_000
    path = jasnah.dataset.get_dataset("laion400m_metadata")
    ds = jasnah.dataset.load_dataset("laion400m_metadata")

    processed = path / "processed"
    processed.mkdir(exist_ok=True, parents=True)

    ds_description = datasets.Dataset.from_generator(
        generate_descriptions,
        gen_kwargs={
            "input": [ds for _ in range(NUM_PROCESS)],
            "samples": list(chunkify(n, NUM_PROCESS)),
            "pos": list(range(NUM_PROCESS)),
        },
        num_proc=NUM_PROCESS,
        features=datasets.Features(
            {
                "image": datasets.Image(),
                "description": datasets.Value("string"),
            }
        ),
    )
    ds_description.save_to_disk(str(processed / f"descriptions{SUFFIX}"))


if __name__ == "__main__":
    main()
