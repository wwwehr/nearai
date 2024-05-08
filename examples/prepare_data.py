"""
Convert raw school math dataset, into Dataset format.
"""

import json
import tarfile

from datasets import Dataset, DatasetDict

from jasnah.dataset import get_dataset
from jasnah.registry import dataset

COLUMNS = [
    "nc_work_spec",
    "is_leaf",
    "is_chapter",
    "problem",
    "solution",
    "answer",
    "chapter",
    "children",
    "answer_kind",
    "task_invalid_reason",
    "nc_worker_comment",
    "et_problem",
    "source_file",
]


def main():
    # Download the raw dataset. This will download the file ac.tar.gz
    dataset_path = get_dataset("test/school_math/raw")

    uncompressed = dataset_path / "uncompressed"
    processed_dataset = dataset_path / "final_dataset"

    if not uncompressed.exists():
        with tarfile.open(dataset_path / "ac.tar.gz") as f:
            f.extractall(uncompressed)

    if not processed_dataset.exists():

        ds = {col: [] for col in COLUMNS}
        sources = []

        for file in uncompressed.glob("*.txt"):
            sources.append(file.name)

            with open(file) as f:
                for line in f:
                    line = line.strip(" \n").replace("\\\\", "\\")

                    doc = json.loads(line)
                    doc["source_file"] = file.name

                    for k, v in ds.items():
                        v.append(doc.get(k, None))

        ds = Dataset.from_dict(ds)
        ds.save_to_disk(str(processed_dataset))

    dataset.upload(processed_dataset, "test/school_math/v1")


if __name__ == "__main__":
    main()
