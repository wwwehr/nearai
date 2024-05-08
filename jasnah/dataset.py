from pathlib import Path

from datasets import Dataset, concatenate_datasets

from jasnah.registry import dataset


def get_dataset(name: str) -> Path:
    """
    Download the dataset from the registry and download it locally if it hasn't been downloaded yet.

    :param name: The name of the dataset to download
    :return: The path to the downloaded dataset
    """
    return dataset.download(name)


def load_dataset(name: str) -> Dataset:
    path = get_dataset(name)
    # https://discuss.huggingface.co/t/solved-how-to-load-multiple-arrow-files-into-one-dataset/49286/4
    return concatenate_datasets(
        [Dataset.from_file(str(file)) for file in sorted(path.glob("*.arrow"))]
    )
