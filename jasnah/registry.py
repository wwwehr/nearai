import os
from pathlib import Path

import boto3

from jasnah.config import CONFIG, DATA_FOLDER


def upload_file(client, path: Path, s3_path: str) -> None:
    assert path.is_file()
    assert path.exists()

    print(f"Uploading {path} to s3://{CONFIG.s3_bucket}/{s3_path}")
    client.upload_file(str(path), CONFIG.s3_bucket, s3_path)


def download_file(s3_client, s3_path: str, local_path: Path):
    if not os.path.exists(os.path.dirname(local_path)):
        os.makedirs(os.path.dirname(local_path))

    s3_client.download_file(CONFIG.s3_bucket, s3_path, local_path)
    print(f"Downloaded s3://{CONFIG.s3_bucket}/{s3_path} to {local_path}")


def download_directory(s3_prefix, local_directory: Path):
    s3_client = boto3.client("s3")
    paginator = s3_client.get_paginator("list_objects_v2")

    found_file = False

    for page in paginator.paginate(Bucket=CONFIG.s3_bucket, Prefix=s3_prefix):
        if "Contents" not in page:
            continue

        for s3_object in page["Contents"]:
            s3_key = s3_object["Key"]
            relative_path = os.path.relpath(s3_key, s3_prefix)
            local_path = local_directory / relative_path

            # Skip directories, S3 keys ending with '/' are folders
            if not s3_key.endswith("/"):
                download_file(s3_client, s3_key, local_path)
                found_file = True

    assert found_file, f"No files found in {s3_prefix}"


class Registry:
    def __init__(self, category: str):
        assert category in ["datasets", "models"]

        self.category = category
        self.download_folder = DATA_FOLDER / category

        if not self.download_folder.exists():
            self.download_folder.mkdir(parents=True, exist_ok=True)

    def upload(self, path: Path, name: str):
        # TODO: Check if there is an existing element in the database with the same name
        # TODO: Add the element to the database

        assert path.exists(), "Path does not exist"

        prefix = os.path.join(CONFIG.s3_prefix, self.category, name)
        s3_client = boto3.client("s3")

        if path.is_file():
            upload_file(s3_client, path, os.path.join(prefix, path.name))

        elif path.is_dir():
            for root, _, files in os.walk(path):
                for filename in files:
                    # Construct full local path
                    local_path = os.path.join(root, filename)

                    # Construct relative path for S3
                    relative_path = os.path.relpath(local_path, path)
                    s3_path = os.path.join(prefix, relative_path)

                    upload_file(s3_client, Path(local_path), s3_path)

    def download(self, name: str):
        target = self.download_folder / name

        if not target.exists():
            prefix = os.path.join(CONFIG.s3_prefix, self.category, name)
            source = f"s3://{CONFIG.s3_bucket}/{prefix}"
            print(f"Downloading {name} from {source} to {target}")
            download_directory(prefix, target)

        return target

    def list(self):
        raise NotImplementedError()


dataset = Registry("datasets")
model = Registry("models")
