from pathlib import Path
from typing import Union

from datasets import Dataset, DatasetDict, load_from_disk  # type: ignore[attr-defined]

from nearai.registry import registry


def get_dataset(name: str) -> Path:
    """Download the dataset from the registry if it hasn't been downloaded yet.

    :param name:
    :return: The path to the downloaded dataset
    """
    return registry.download(name)


def load_dataset(alias_or_name: str) -> Union[Dataset, DatasetDict]:
    path = get_dataset(alias_or_name)
    return load_from_disk(path.as_posix())
