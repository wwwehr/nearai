"""
Converts processed school math dataset, into json format for training.
"""

import subprocess

from jasnah.dataset import get_dataset
from jasnah.model import get_model


def main():
    dataset_path = get_dataset("school_math_ru/transformed/v0")
    input = dataset_path / "training_data.json"
    output_prefix = dataset_path / "training_data"
    vocab = get_model("gpt2-vocab.json") / "gpt2-vocab.json"
    merges = get_model("gpt2-merges.txt") / "gpt2-merges.txt"

    command = f"""
    python third_party/Megatron-LM/tools/preprocess_data.py
        --input {input}
        --output-prefix {output_prefix}
        --vocab {vocab}
        --dataset-impl mmap
        --tokenizer-type GPT2BPETokenizer
        --merge-file {merges}
        --append-eod
        --workers 1
        --chunk-size 1000000000
    """
    # Split the command into a list
    process = subprocess.Popen(
        command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Get output and errors, if any
    stdout, stderr = process.communicate()

    if process.returncode == 0:
        print("Command executed successfully!")
        print("Output:", stdout.decode())
    else:
        print("Error in command execution")
        print("Error:", stderr.decode())


if __name__ == "__main__":
    main()
