from pathlib import Path
from typing import Union

from datasets import Dataset, DatasetDict, load_from_disk  # type: ignore[attr-defined]

from nearai.registry import registry


def get_dataset(name: str, verbose: bool = True) -> Path:
    """Download the dataset from the registry and download it locally if it hasn't been downloaded yet.

    :param name: The name of the entry to download the dataset. The format should be namespace/name/version.
    :return: The path to the downloaded dataset
    """
    return registry.download(name, verbose=verbose)


def load_dataset(alias_or_name: str, verbose: bool = True) -> Union[Dataset, DatasetDict]:
    """Load a dataset from the registry."""
    path = get_dataset(alias_or_name, verbose=verbose)
    return load_from_disk(path.as_posix())
