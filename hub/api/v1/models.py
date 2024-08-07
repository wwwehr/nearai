from contextlib import contextmanager
from datetime import datetime
from os import getenv
from typing import Iterator, Optional

from dotenv import load_dotenv
from sqlmodel import Field, Session, SQLModel, UniqueConstraint, create_engine

load_dotenv()

S3_BUCKET = getenv("S3_BUCKET")
S3_PREFIX = getenv("S3_PREFIX")
DB_HOST = getenv("DATABASE_HOST")
DB_USER = getenv("DATABASE_USER")
DB_PASSWORD = getenv("DATABASE_PASSWORD")
DB_NAME = getenv("DATABASE_NAME")


class RegistryEntry(SQLModel, table=True):
    """Project stored in the registry."""

    __table_args__ = (UniqueConstraint("namespace", "name", "version", name="unique_project"),)

    id: int = Field(default=None, primary_key=True)
    namespace: str = Field(nullable=False)
    name: str = Field(nullable=False)
    version: str = Field(nullable=False)
    time: datetime = Field(default_factory=datetime.now, nullable=False)
    description: str = Field(default="", nullable=False)
    show_entry: bool = Field(default=True)

    def get_key(self, object: Optional[str] = None) -> str:
        """Get the key to the project or object in S3."""
        assert S3_PREFIX is not None
        key = f"{S3_PREFIX}/{self.namespace}/{self.name}/{self.version}"
        if object is not None:
            key = f"{key}/{object}"
        return key


class Tags(SQLModel, table=True):
    """Many-to-many table between registry entries and tags."""

    registry_id: int = Field(foreign_key="registryentry.id", primary_key=True)
    tag: str = Field(primary_key=True)


engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")

SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
