import os
from pathlib import Path
import json

import datasets


def main():
    path = Path("/home/setup/.jasnah/registry/datasets/ncimages_ru/raw/v0/processed/")

    num_cpu = os.cpu_count() or 8
    test_percent = 0.1
    shard_size = 4 * 1024**3  # 4GB

    for ds_name in ["descriptions", "leading"]:
        ds_path = path / ds_name
        ds = datasets.Dataset.load_from_disk(str(ds_path))

        new_ds_path = path / f"{ds_name}_split"
        new_ds_path.mkdir(parents=True, exist_ok=True)

        size = ds.size_in_bytes
        size_per_row = size / len(ds)
        rows_per_shard = max(int(shard_size / size_per_row), 1)

        ds_split = ds.train_test_split(test_size=test_percent, seed=0)

        for name, split in ds_split.items():
            assert isinstance(name, str)
            assert isinstance(split, datasets.Dataset)

            new_path = new_ds_path / name

            num_shards = (len(split) + rows_per_shard - 1) // rows_per_shard
            num_proc = min(num_shards, num_cpu)

            print(ds_name, name, len(split), num_proc, num_shards)
            split.save_to_disk(str(new_path), num_proc=num_proc, num_shards=num_shards)

        with open(new_ds_path / "dataset_dict.json", "w") as f:
            json.dump(dict(splits=["train", "test"]), f)


def test():
    ds = datasets.DatasetDict.load_from_disk(
        "/home/setup/.jasnah/registry/datasets/ncimages_ru/raw/v0/processed/leading_split"
    )
    print(ds)


if __name__ == "__main__":
    test()
