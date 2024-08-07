import inspect
import re
from io import BytesIO
from os import getenv
from typing import Annotated, List

import boto3
import botocore
import botocore.exceptions
from dotenv import load_dotenv
from fastapi import Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import AfterValidator, BaseModel
from sqlmodel import delete, select, text

from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.models import RegistryEntry, Tags, get_session
from hub.api.v1.routes import v1_router

load_dotenv()
S3_BUCKET = getenv("S3_BUCKET")

s3 = boto3.client("s3")


# Code from: https://stackoverflow.com/a/77113651/4950797
def as_form(cls):
    new_params = [
        inspect.Parameter(
            field_name,
            inspect.Parameter.POSITIONAL_ONLY,
            default=model_field.default,
            annotation=Annotated[model_field.annotation, *model_field.metadata, Form()],
        )
        for field_name, model_field in cls.model_fields.items()
    ]

    cls.__signature__ = cls.__signature__.replace(parameters=new_params)

    return cls


identifier_pattern = re.compile(r"^[a-zA-Z0-9_\-.]+$")


def valid_identifier(identifier: str) -> str:
    result = identifier_pattern.match(identifier)
    if result is None:
        raise HTTPException(
            status_code=400, detail=f"Invalid identifier: {repr(identifier)}. Should match {identifier_pattern.pattern}"
        )
    return result[0]


tag_pattern = re.compile(r"^[a-zA-Z0-9_\-]+$")


def valid_tag(tag: str) -> bool:
    return tag_pattern.match(tag) is not None


@as_form
class ProjectLocation(BaseModel):
    namespace: Annotated[str, AfterValidator(valid_identifier)]
    name: Annotated[str, AfterValidator(valid_identifier)]
    version: Annotated[str, AfterValidator(valid_identifier)]


def with_write_access(use_forms=False):
    default = Depends() if use_forms else Body()

    def fn_with_write_access(
        project: ProjectLocation = default,
        auth: AuthToken = Depends(revokable_auth),
    ) -> ProjectLocation:
        """Check the user has write access to the project."""
        if auth.account_id != project.namespace:
            raise HTTPException(
                status_code=403, detail=f"Unauthorized. Namespace: {project.namespace} != Account: {auth.account_id}"
            )
        return project

    return fn_with_write_access


def get_or_create(project: ProjectLocation = Depends(with_write_access())) -> RegistryEntry:
    with get_session() as session:
        entry = session.exec(
            select(RegistryEntry).where(
                RegistryEntry.namespace == project.namespace,
                RegistryEntry.name == project.name,
                RegistryEntry.version == project.version,
            )
        ).first()

        if entry is None:
            entry = RegistryEntry(namespace=project.namespace, name=project.name, version=project.version)
            session.add(entry)
            session.commit()

        return entry


def get(project: ProjectLocation = Depends()) -> RegistryEntry:
    with get_session() as session:
        entry = session.exec(
            select(RegistryEntry).where(
                RegistryEntry.namespace == project.namespace,
                RegistryEntry.name == project.name,
                RegistryEntry.version == project.version,
            )
        ).first()

        if entry is None:
            raise HTTPException(status_code=404, detail="Project not found")

        return entry


class ProjectMetadataInput(BaseModel):
    description: str
    authors: List[str]
    tags: List[str]
    show_entry: bool


class ProjectMetadata(ProjectMetadataInput):
    name: str
    version: str


def check_file_exists(key):
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


@v1_router.post("/registry/upload_file")
async def upload_file(
    project: ProjectLocation = Depends(with_write_access(use_forms=True)),
    path: str = Form(...),
    file: UploadFile = File(...),
):
    entry = get(project)
    key = entry.get_key(path)

    if check_file_exists(key):
        raise HTTPException(status_code=400, detail=f"File {key} already exists.")

    s3.upload_fileobj(file.file, S3_BUCKET, key)

    return {"status": "File uploaded", "path": key}


@v1_router.post("/registry/download_file")
async def download_file(
    project: RegistryEntry = Depends(get),
    path: str = Body(),
):
    # https://stackoverflow.com/a/71126498/4950797
    object = s3.get_object(Bucket=S3_BUCKET, Key=project.get_key(path))
    return StreamingResponse(object["Body"].iter_chunks(), media_type="application/octet-stream")


@v1_router.post("/registry/upload_metadata")
async def upload_metadata(project: RegistryEntry = Depends(get_or_create), metadata: ProjectMetadataInput = Body()):
    with get_session() as session:
        full_metadata = ProjectMetadata(name=project.name, version=project.version, **metadata.model_dump())

        if project.description != full_metadata.description:
            project.description = full_metadata.description
            session.add(project)

        buffer = BytesIO(full_metadata.model_dump_json().encode())
        s3.upload_fileobj(buffer, S3_BUCKET, project.get_key("metadata.json"))

        # Delete all previous tags
        session.exec(delete(Tags).where(Tags.registry_id == project.id))

        # Add the new tags
        if len(full_metadata.tags) > 0:
            tags = [Tags(registry_id=project.id, tag=tag) for tag in full_metadata.tags]
            session.add_all(tags)

        session.commit()

        return {"status": "Updated metadata", "namespace": project.namespace, "metadata": full_metadata.model_dump()}


@v1_router.post("/registry/download_metadata")
async def download_metadata(project: RegistryEntry = Depends(get)) -> ProjectMetadata:
    buffer = BytesIO()
    s3.download_fileobj(S3_BUCKET, project.get_key("metadata.json"), buffer)
    return ProjectMetadata.model_validate_json(buffer.getvalue().decode())


@v1_router.post("/registry/list_files")
async def list_files(project: RegistryEntry = Depends(get)) -> List[str]:
    """List all files that belong to a project."""
    key = project.get_key() + "/"
    objects = s3.list_objects(Bucket=S3_BUCKET, Prefix=key)
    files = [obj["Key"][len(key) :] for obj in objects.get("Contents", [])]
    return files


@v1_router.post("/registry/list_projects")
async def list_projects(
    tags: str = "",
    total: int = 32,
    show_hidden: bool = False,
) -> List[ProjectLocation]:
    tags_list = list({tag for tag in tags.split(",") if tag})

    with get_session() as session:
        if len(tags_list) == 0:
            query = select(RegistryEntry)
            if not show_hidden:
                query = query.where(RegistryEntry.show_entry)

            query = query.limit(total).order_by(RegistryEntry.id.desc())

            result = session.exec(query).all()
            return [
                ProjectLocation(namespace=entry.namespace, name=entry.name, version=entry.version) for entry in result
            ]
        else:
            assert all(valid_tag(tag) for tag in tags_list)
            tags_input = ",".join(f"'{tag}'" for tag in tags_list)

            query = f"""WITH FilteredRegistry AS (
                    SELECT registry.id FROM registryentry registry
                    JOIN tags ON registry.id = tags.registry_id
                    WHERE show_entry >= {1 - int(show_hidden)} AND tags.tag IN ({tags_input})
                    GROUP BY registry.id
                    HAVING COUNT(DISTINCT tags.tag) = {len(tags_list)}
                    ),
                    RankedRegistry AS (
                        SELECT id, ROW_NUMBER() OVER (ORDER BY id DESC) AS col_rank
                        FROM FilteredRegistry
                    )

                    SELECT registry.id, registry.namespace, registry.name, registry.version,
                           tags.tag FROM RankedRegistry ranked
                    JOIN registryentry registry ON ranked.id = registry.id
                    JOIN tags ON registry.id = tags.registry_id
                    WHERE ranked.col_rank <= {total}
                    ORDER BY registry.id DESC
                """

            result = session.exec(text(query)).all()
            # (1, 'au.near', 'test-000', '0.0.1', 'bar')
            filtered = {}

            for id, namespace, name, version, _ in result:
                if id not in filtered:
                    filtered[id] = (namespace, name, version)

            final = sorted(filtered.items(), key=lambda x: x[0], reverse=True)
            return [
                ProjectLocation(namespace=namespace, name=name, version=version)
                for _, (namespace, name, version) in final
            ]
