import shutil
import sys
from pathlib import Path


def filter_checkpoints(src_folder: Path, target_folder: Path):
    checkpoints = []
    for file in src_folder.glob("*.pt"):
        batch_id = file.name.strip("model_.pt")
        batch_id = int(batch_id)
        checkpoints.append((batch_id, file))

    checkpoints.sort()

    keep = []
    last_block = -1
    for num, file in checkpoints:
        block = num // 100_000
        if num == 0 or block > last_block or len(keep) == 1:
            keep.append(file)
        last_block = block
        keep[-1] = file

    for file in keep:
        shutil.copy2(file, target_folder)


def check_model():
    pass


if __name__ == "__main__":
    checkpoint_folder = Path(sys.argv[1])
    target_folder = Path(sys.argv[2])
    filter_checkpoints(checkpoint_folder, target_folder)
