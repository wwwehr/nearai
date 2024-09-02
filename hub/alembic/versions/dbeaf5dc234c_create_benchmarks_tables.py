"""Create benchmarks tables.

Revision ID: dbeaf5dc234c
Revises: 0c1df68a1460
Create Date: 2024-08-29 13:25:15.457619

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dbeaf5dc234c"
down_revision: Union[str, None] = "0c1df68a1460"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "benchmarks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("namespace", sa.String(64), nullable=False),
        sa.Column("benchmark", sa.Text, nullable=False),
        sa.Column("solver", sa.Text, nullable=False),
        sa.Column("args", sa.Text, nullable=False),
    )

    op.create_table(
        "benchmark_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("benchmark_id", sa.Integer, nullable=False),
        sa.Column("index", sa.Integer, nullable=False),
        sa.Column("solved", sa.Boolean, nullable=False),
        sa.Column("info", sa.JSON, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("benchmark_results")
    op.drop_table("benchmarks")
