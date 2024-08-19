"""Create table completions.

Revision ID: ddc68957516f
Revises:
Create Date: 2024-08-14 13:02:47.007157

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ddc68957516f"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "completions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("response", sa.Text, nullable=False),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("endpoint", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP, nullable=False, server_default=sa.func.current_timestamp()),
    )

    op.create_index("completions_account_id_idx", "completions", ["account_id"])


def downgrade() -> None:
    op.drop_index("completions_account_id_idx", table_name="completions")
    op.drop_table("completions")
