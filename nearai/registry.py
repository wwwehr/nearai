import os
from pathlib import Path
from typing import List, Optional, Union

import boto3
from openapi_client.api.registry_api import (
    BodyDownloadMetadataV1RegistryDownloadMetadataPost,
    ProjectLocation,
    ProjectMetadata,
    RegistryApi,
)
from openapi_client.exceptions import NotFoundException

import nearai
from nearai.config import CONFIG, DATA_FOLDER
from nearai.db import DisplayRegistry, RegistryEntry, db


class Registry:
    def __init__(self):
        """Create Registry object to interact with the registry programatically."""
        self.download_folder = DATA_FOLDER / "registry"
        self.api = RegistryApi()

        if not self.download_folder.exists():
            self.download_folder.mkdir(parents=True, exist_ok=True)

    def update(self, project: ProjectLocation, metadata: ProjectMetadata):
        """Update metadata of a project in the registry."""
        self.api.upload_metadata_v1_registry_upload_metadata_post()

        raise NotImplementedError()

    def info(self, project: ProjectLocation) -> Optional[ProjectMetadata]:
        """Get metadata of a project in the registry."""
        try:
            return self.api.download_metadata_v1_registry_download_metadata_post(
                BodyDownloadMetadataV1RegistryDownloadMetadataPost.from_dict(dict(project=project))
            )
        except NotFoundException:
            return None

    def upload(self, project: ProjectLocation, local_path: Path):
        raise NotImplementedError()

    def download(self, project: ProjectLocation):
        raise NotImplementedError()

    def upload_file(self, project: ProjectLocation, local_path: Path, path: Path):
        raise NotImplementedError()

    def download_file(self, project: ProjectLocation, path: Path, local_path: Path):
        raise NotImplementedError()

    def list(self) -> List[ProjectMetadata]:
        raise NotImplementedError()

    # def add(  # noqa: D102
    #     self,
    #     *,
    #     s3_path: str,
    #     name: Optional[str],
    #     author: str,
    #     description: Optional[str],
    #     details: Optional[dict],
    #     show_entry: bool,
    #     tags: List[str],
    # ) -> int:
    #     if db.exists_in_registry(s3_path):
    #         raise ValueError(f"{s3_path} already exists in the registry")

    #     registry_id = db.add_to_registry(
    #         s3_path=s3_path,
    #         name=name or "",
    #         author=author,
    #         description=description,
    #         details=details,
    #         show_entry=show_entry,
    #         tags=self._all_tags(tags),
    #     )

    #     nearai.log(target="Add to registry", name=name, author=author)
    #     return int(registry_id)

    # def add_tags(self, *, identifier: Union[str, int], tags: List[str]) -> None:  # noqa: D102
    #     entry = db.get_registry_entry_by_identifier(identifier)
    #     assert entry is not None

    #     current_tags = db.get_tags(entry.id)

    #     all_tags = list(set(current_tags + tags))
    #     if len(all_tags) != len(current_tags) + len(tags):
    #         raise ValueError(f"Some tags are already present. New tags: {tags} Current tags: {current_tags}")

    #     for tag in tags:
    #         db.add_tag(registry_id=entry.id, tag=tag)

    # def remove_tag(self, *, identifier: Union[str, int], tag: str) -> None:  # noqa: D102
    #     entry = db.get_registry_entry_by_identifier(identifier)
    #     assert entry is not None

    #     current_tags = db.get_tags(entry.id)

    #     if tag not in current_tags:
    #         raise ValueError(f"Tag {tag} is not present in {identifier}")

    #     db.remove_tag(registry_id=entry.id, tag=tag)

    # def upload(  # noqa: D102
    #     self,
    #     *,
    #     path: Path,
    #     s3_path: str,
    #     author: str,
    #     description: Optional[str],
    #     name: Optional[str],
    #     details: Optional[dict],
    #     show_entry: bool,
    #     tags: List[str],
    # ) -> int:
    #     assert path.exists(), "Path does not exist"

    #     prefix = os.path.join(CONFIG.s3_prefix, s3_path)

    #     if self.exists_in_s3(s3_path):
    #         raise ValueError(f"{prefix} already exists in S3")

    #     registry_id = self.add(
    #         s3_path=s3_path,
    #         name=name,
    #         author=author,
    #         description=description,
    #         details=details,
    #         show_entry=show_entry,
    #         tags=tags,
    #     )

    #     nearai.log(target="Upload to S3", path=s3_path, author=author)

    #     s3_client = boto3.client("s3")

    #     if path.is_file():
    #         upload_file(s3_client, os.path.join(prefix, path.name), path)

    #     elif path.is_dir():
    #         for root, _, files in os.walk(path):
    #             for filename in files:
    #                 # Construct full local path
    #                 local_path = os.path.join(root, filename)

    #                 # Construct relative path for S3
    #                 relative_path = os.path.relpath(local_path, path)
    #                 s3_path = os.path.join(prefix, relative_path)

    #                 upload_file(s3_client, s3_path, Path(local_path))
    #     return registry_id

    # def download(self, identifier: Union[str, int], version: Optional[str] = None) -> Path:  # noqa: D102
    #     # Try to work in offline mode by checking if identifier is a path first before fetching from database.
    #     if isinstance(identifier, str) and not identifier.isdigit():
    #         target = self.download_folder / identifier
    #         if target.exists():
    #             return target

    #     entry = db.get_registry_entry_by_identifier(identifier, version=version)
    #     assert entry is not None

    #     path = entry.path
    #     target = self.download_folder / entry.path

    #     if not target.exists():
    #         prefix = os.path.join(CONFIG.s3_prefix, path)
    #         source = f"s3://{CONFIG.s3_bucket}/{prefix}"
    #         print(f"Downloading {path} from {source} to {target}")
    #         nearai.log(target="Download from S3", name=identifier)
    #         download_directory(prefix, target)

    #     return target

    # def list(self, *, tags: List[str], total: int, show_all: bool) -> List[DisplayRegistry]:  # noqa: D102
    #     tags = self._all_tags(tags)
    #     result: List[DisplayRegistry] = db.list_registry_entries(total=total, show_all=show_all, tags=tags)
    #     return result

    # def get_entry(self, identifier: Union[str, int], version: Optional[str] = None) -> Union[RegistryEntry, None]:
    #     """Get a specific entry from the registry."""
    #     return db.get_registry_entry_by_identifier(identifier, version=version)

    # def get_file(
    #     self, identifier: Union[str, int], file: Optional[str] = None, version: Optional[str] = None
    # ) -> Union[bytes, None]:
    #     """Download a specific file from the registry."""
    #     entry = db.get_registry_entry_by_identifier(identifier, version=version)
    #     if entry is None:
    #         return None

    #     s3_client = boto3.client("s3")

    #     if file is None:
    #         # list files below the prefix
    #         s3_path = CONFIG.s3_prefix + "/" + entry.path
    #         list = s3_client.list_objects_v2(Bucket=CONFIG.s3_bucket, Prefix=s3_path)
    #         if "Contents" not in list:
    #             return None
    #         # get first filename
    #         file = list["Contents"][0]["Key"].split("/")[-1]

    #     s3_path = "registry/" + entry.path + (f"/{file}" if file else "")
    #     source = f"s3://{CONFIG.s3_bucket}/{s3_path}"
    #     print(f"Downloading {s3_path} from {source}")
    #     nearai.log(target="Download from S3", name=identifier)
    #     try:
    #         response = s3_client.get_object(Bucket=CONFIG.s3_bucket, Key=s3_path)
    #     except s3_client.exceptions.NoSuchKey:
    #         return None
    #     return response["Body"].read()


registry = Registry()
