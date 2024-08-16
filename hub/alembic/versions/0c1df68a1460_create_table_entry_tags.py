"""Create table entry_tags.

Revision ID: 0c1df68a1460
Revises: fce1ee10b43d
Create Date: 2024-08-14 13:50:03.790108

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0c1df68a1460"
down_revision: Union[str, None] = "fce1ee10b43d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entry_tags",
        sa.Column("registry_id", sa.Integer, primary_key=True),
        sa.Column("tag", sa.String(255), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("entry_tags")
