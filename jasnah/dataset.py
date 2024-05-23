from pathlib import Path

from datasets import Dataset, concatenate_datasets, load_from_disk

from jasnah.registry import dataset


def get_dataset(alias_or_name: str) -> Path:
    """
    Download the dataset from the registry and download it locally if it hasn't been downloaded yet.

    :param name: The name of the dataset to download
    :return: The path to the downloaded dataset
    """
    return dataset.download(alias_or_name)


def load_dataset(alias_or_name: str) -> Dataset:
    path = get_dataset(alias_or_name)
    return load_from_disk(path.as_posix())
