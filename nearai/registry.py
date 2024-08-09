from pathlib import Path
from shutil import copyfileobj
from typing import Any, Dict, List, Optional

from openapi_client import ProjectLocation, ProjectMetadata, ProjectMetadataInput
from openapi_client.api.registry_api import (
    BodyDownloadFileV1RegistryDownloadFilePost,
    BodyDownloadMetadataV1RegistryDownloadMetadataPost,
    BodyListFilesV1RegistryListFilesPost,
    BodyUploadMetadataV1RegistryUploadMetadataPost,
    RegistryApi,
)
from openapi_client.exceptions import BadRequestException, NotFoundException
from tqdm import tqdm

# Note: We should import nearai.config on this file to make sure the method setup_api_client is called at least once
#       before creating RegistryApi object. This is because setup_api_client sets the default configuration for the
#       API client that is used by Registry API.
from nearai.config import DATA_FOLDER


class Registry:
    def __init__(self):
        """Create Registry object to interact with the registry programatically."""
        self.download_folder = DATA_FOLDER / "registry"
        self.api = RegistryApi()

        if not self.download_folder.exists():
            self.download_folder.mkdir(parents=True, exist_ok=True)

    def update(self, project: ProjectLocation, metadata: ProjectMetadataInput) -> Dict[str, Any]:
        """Update metadata of a project in the registry."""
        result = self.api.upload_metadata_v1_registry_upload_metadata_post(
            BodyUploadMetadataV1RegistryUploadMetadataPost(metadata=metadata, project=project)
        )
        return result

    def info(self, project: ProjectLocation) -> Optional[ProjectMetadata]:
        """Get metadata of a project in the registry."""
        try:
            return self.api.download_metadata_v1_registry_download_metadata_post(
                BodyDownloadMetadataV1RegistryDownloadMetadataPost.from_dict(dict(project=project))
            )
        except NotFoundException:
            return None

    def upload_file(self, project: ProjectLocation, local_path: Path, path: Path) -> bool:
        """Upload a file to the registry."""
        with open(local_path, "rb") as file:
            data = file.read()

            try:
                self.api.upload_file_v1_registry_upload_file_post(
                    path=str(path),
                    file=data,
                    namespace=project.namespace,
                    name=project.name,
                    version=project.version,
                )
                return True
            except BadRequestException as e:
                if "already exists" in e.body:
                    return False

                raise e

    def download_file(self, project: ProjectLocation, path: Path, local_path: Path):
        """Download a file from the registry."""
        result = self.api.download_file_v1_registry_download_file_post_without_preload_content(
            BodyDownloadFileV1RegistryDownloadFilePost.from_dict(
                dict(
                    project=project,
                    path=str(path),
                )
            )
        )

        local_path.parent.mkdir(parents=True, exist_ok=True)

        with open(local_path, "wb") as f:
            copyfileobj(result, f)

    def download(
        self,
        project: ProjectLocation,
        force: bool = False,
        show_progress: bool = False,
    ) -> Path:
        """Download project from the registry locally."""
        files = registry.list_files(project)

        download_path = DATA_FOLDER / "registry" / project.namespace / project.name / project.version

        if download_path.exists():
            if not force:
                print(f"Project {project} already exists at {download_path}. Use --force to overwrite the project.")
                return download_path

        download_path.mkdir(parents=True, exist_ok=True)

        metadata = registry.info(project)

        if metadata is None:
            print(f"Project {project} not found.")
            return

        metadata_path = download_path / "metadata.json"
        with open(metadata_path, "w") as f:
            f.write(metadata.model_dump_json(indent=2))

        for file in (pbar := tqdm(files, disable=not show_progress)):
            pbar.set_description(file)
            registry.download_file(project, file, download_path / file)

    def list_files(self, project: ProjectLocation) -> List[str]:
        """List files in a project in the registry.

        Return the relative paths to all files with respect to the root of the project.
        """
        return self.api.list_files_v1_registry_list_files_post(
            BodyListFilesV1RegistryListFilesPost.from_dict(dict(project=project))
        )

    def list(
        self,
        category: str,
        tags: str,
        total: int,
        show_hidden: bool,
    ) -> List[ProjectLocation]:
        """List and filter projects in the registry."""
        return self.api.list_projects_v1_registry_list_projects_post(
            category=category,
            tags=tags,
            total=total,
            show_hidden=show_hidden,
        )


registry = Registry()
