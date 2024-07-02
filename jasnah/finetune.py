from random import randint
from subprocess import run
from typing import Any, Dict, List, Mapping, Optional
from pathlib import Path

from datasets import load_from_disk
from torch.utils.data import Dataset
from torchtune.modules.tokenizers import Tokenizer

from jasnah import timestamp
from jasnah.config import CONFIG, DATA_FOLDER
from jasnah.model import get_model
from jasnah.registry import registry
from jasnah.server import ServerClient
from jasnah.dataset import get_dataset


class FinetuneCli:
    def submit(
        self,
        model: str,
        tokenizer: str,
        dataset: str,
        num_procs: int,
        num_nodes: int = 1,
        job_id: Optional[str] = None,
        checkpoint: Optional[str] = None,
        epochs: int = 1,
    ):
        """Submit a finetuning job to the cluster"""
        client = ServerClient(CONFIG.server_url)

        result = client.submit(
            "finetune-task",
            "https://github.com/nearai/jasnah-cli.git",
            "main",
            f"jasnah-cli finetune start --model {model} --tokenizer {tokenizer} --dataset {dataset} --num_procs {num_procs} --num_nodes {num_nodes} --job_id {job_id} --checkpoint {checkpoint} --epochs {epochs}",
            CONFIG.db_user,
            None,
            num_nodes,
        )

        print(result)

    def start(
        self,
        model: str,
        tokenizer: str,
        dataset: str,
        column: str,
        num_procs: int,
        format: str,
        split: str = 'train',
        num_nodes: int = 1,
        job_id: Optional[str] = None,
        checkpoint: Optional[str] = None,
    ):
        """Start a finetuning job on the current node"""
        if job_id is None:
            job_id = "job"
        job_id = f"{job_id}-{timestamp()}-{randint(10**8, 10**9 - 1)}"
        job_folder = DATA_FOLDER / "finetune" / job_id
        job_folder.mkdir(parents=True, exist_ok=True)

        configs = Path(__file__).parent.parent / "etc" / "finetune"
        config_path = configs / f"{format}.yml"

        CONFIG_TEMPLATE = config_path.read_text()
        assert num_nodes >= 1

        model_path = get_model(model)

        tokenizer_path = registry.download(tokenizer) / "tokenizer.model"
        assert tokenizer_path.exists(), f"tokenizer.model not found in {tokenizer_path}"

        checkpoint_path = get_model(checkpoint) if checkpoint else "null"

        dataset_path = get_dataset(dataset)

        config = job_folder / "config.yaml"
        with open(config, "w") as f:
            f.write(
                CONFIG_TEMPLATE.format(
                    TOKENIZER=str(tokenizer_path),
                    MODEL=str(model_path),
                    RECIPE_CHECKPOINT=checkpoint_path,
                    CHECKPOINT_OUTPUT_DIR=str(job_folder / "checkpoint_output"),
                    DATASET=dataset_path,
                    DATASET_COLUMN=column,
                    DATASET_SPLIT=split,
                    LOGGING_OUTPUT_DIR=str(job_folder / "logs"),
                )
            )

        print("Starting job at", job_folder)

        if num_nodes == 1:
            run(
                [
                    "tune",
                    "run",
                    "--nproc_per_node",
                    str(num_procs),
                    "lora_finetune_distributed",
                    "--config",
                    str(config),
                ]
            )
        else:
            # Fetch rank and master addr from environment variables
            raise NotImplementedError()

    def inspect(self, job_id: str):
        raise NotImplementedError()


def truncate(
    tokens: List[Any],
    max_seq_len: int,
    eos_id: Optional[Any] = None,
) -> List[Any]:
    """
    Truncate a list of tokens to a maximum length. If eos_id is provided, the last
    token will be replaced with eos_id.

    Args:
        tokens (List[Any]): list of tokens to truncate
        max_seq_len (int): maximum length of the list
        eos_id (Optional[Any]): token to replace the last token with. If None, the
            last token will not be replaced. Default is None.

    Returns:
        List[Any]: truncated list of tokens
    """
    tokens_truncated = tokens[:max_seq_len]
    if eos_id is not None and tokens_truncated[-1] != eos_id:
        tokens_truncated[-1] = eos_id
    return tokens_truncated


class TextCompletionDataset(Dataset):
    """
    Freeform dataset for any unstructured text corpus. Quickly load any dataset
    from Hugging Face or local disk and tokenize it for your model.

    Args:
        tokenizer (Tokenizer): Tokenizer used to encode data. Tokenize must implement an ``encode`` and ``decode`` method.
        source (str): path string of dataset, anything supported by Hugging Face's ``load_dataset``
            (https://huggingface.co/docs/datasets/en/package_reference/loading_methods#datasets.load_dataset.path)
        column (str): name of column in the sample that contains the text data. This is typically required
            for Hugging Face datasets or tabular data. For local datasets with a single column, use the default "text",
            which is what is assigned by Hugging Face datasets when loaded into memory. Default is "text".
        max_seq_len (Optional[int]): Maximum number of tokens in the returned input and label token id lists.
            Default is None, disabling truncation. We recommend setting this to the highest you can fit in memory
            and is supported by the model. For example, llama2-7B supports up to 4096 for sequence length.
        **load_dataset_kwargs (Dict[str, Any]): additional keyword arguments to pass to ``load_dataset``.
    """

    def __init__(
        self,
        tokenizer: Tokenizer,
        source: str,
        column: str = "text",
        split: Optional[str] = None,
        max_seq_len: Optional[int] = None,
        **load_dataset_kwargs: Dict[str, Any],
    ) -> None:
        self._tokenizer = tokenizer
        self._data = load_from_disk(source, **load_dataset_kwargs)
        if split is not None:
            self._data = self._data[split]
        self.max_seq_len = max_seq_len
        self._column = column

    def __len__(self):
        return len(self._data)

    def __getitem__(self, index: int) -> Dict[str, List[int]]:
        sample = self._data[index]
        return self._prepare_sample(sample)

    def _prepare_sample(self, sample: Mapping[str, Any]) -> Dict[str, List[int]]:
        prompt = sample[self._column]
        tokens = self._tokenizer.encode(text=prompt, add_bos=True, add_eos=True)

        # Truncate if needed, but don't coerce EOS id
        if self.max_seq_len is not None:
            tokens = truncate(tokens, self.max_seq_len - 1)

        # No need to offset labels by 1 - happens in the recipe
        labels = tokens.copy()

        return {"tokens": tokens, "labels": labels}


def text_completion_dataset(
    tokenizer: Tokenizer,
    source: str,
    column: str = 'text',
    split: str = 'train',
    max_seq_len: Optional[int] = None,
    **load_from_disk_kwargs: Dict[str, Any],
) -> TextCompletionDataset:
    ds = TextCompletionDataset(
        tokenizer=tokenizer,
        source=source,
        column=column,
        split=split,
        max_seq_len=max_seq_len,
        **load_from_disk_kwargs,
    )
    return ds
