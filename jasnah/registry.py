import os
from pathlib import Path
from typing import List, Optional

import boto3

import jasnah
from jasnah.config import CONFIG, DATA_FOLDER
from jasnah.db import RegistryEntry, db


def upload_file(client, path: Path, s3_path: str):
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


def exists_directory_in_s3(s3_path: str) -> bool:
    s3_client = boto3.client("s3")
    response = s3_client.list_objects(
        Bucket=CONFIG.s3_bucket, Prefix=s3_path, Delimiter="/", MaxKeys=1
    )
    return "Contents" in response or "CommonPrefixes" in response


class Registry:
    def __init__(self, category: str):
        assert category in ["datasets", "models"]

        self.category = category
        self.download_folder = DATA_FOLDER / category

        if not self.download_folder.exists():
            self.download_folder.mkdir(parents=True, exist_ok=True)

    def update(
        self,
        id: int,
        *,
        author: Optional[str] = None,
        description: Optional[str] = None,
        alias: Optional[str] = None,
        details: Optional[dict] = None,
        show_entry: Optional[bool] = None,
    ):
        db.update_registry_entry(id, author, description, alias, details, show_entry)

        update = dict(
            author=author,
            description=description,
            alias=alias,
            details=details,
            show_entry=show_entry,
        )
        update = {k: v for k, v in update.items() if v is not None}
        jasnah.log(target=f"Update {self.category} in registry", id=id, **update)

    def exists_in_s3(self, name: str) -> bool:
        prefix = os.path.join(CONFIG.s3_prefix, self.category, name)
        return exists_directory_in_s3(prefix)

    def add(
        self,
        name: str,
        author: str,
        description: Optional[str],
        alias: Optional[str],
        details: Optional[dict],
        show_entry: bool,
    ):
        if db.exists_in_registry(name, self.category):
            raise ValueError(f"{name} already exists in the registry")

        db.add_to_registry(
            name, self.category, author, description, alias, details, show_entry
        )

        jasnah.log(target=f"Add {self.category} to registry", name=name, author=author)

    def upload(
        self,
        path: Path,
        name: str,
        author: str,
        description: Optional[str],
        alias: Optional[str],
        details: Optional[dict],
        show_entry: bool,
    ):
        assert path.exists(), "Path does not exist"

        prefix = os.path.join(CONFIG.s3_prefix, self.category, name)

        if self.exists_in_s3(name):
            raise ValueError(f"{prefix} already exists in S3")

        self.add(name, author, description, alias, details, show_entry)
        jasnah.log(target=f"Upload {self.category} to S3", name=name, author=author)

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

    def download(self, alias_or_name: str):
        entry = db.get_registry_entry_by_alias_or_name(alias_or_name)

        if entry is None:
            raise ValueError(f"{alias_or_name} not found in the registry")

        jasnah.log(target=f"Download {self.category} from S3", name=alias_or_name)

        name = entry.name
        target = self.download_folder / entry.name

        if not target.exists():
            prefix = os.path.join(CONFIG.s3_prefix, self.category, name)
            source = f"s3://{CONFIG.s3_bucket}/{prefix}"
            print(f"Downloading {name} from {source} to {target}")
            download_directory(prefix, target)

        return target

    def list(self) -> List[RegistryEntry]:
        return db.list_registry_entries(self.category)


dataset = Registry("datasets")
model = Registry("models")
