"""Create table nonces.

Revision ID: 854b55665dda
Revises: ddc68957516f
Create Date: 2024-08-14 13:13:59.147980

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "854b55665dda"
down_revision: Union[str, None] = "ddc68957516f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nonces",
        sa.Column("nonce", sa.String(32)),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("recipient", sa.String(64), nullable=False),
        sa.Column("callback_url", sa.Text, nullable=False),
        sa.Column("nonce_status", sa.Enum("active", "revoked"), nullable=False),
        sa.Column("first_seen_at", sa.TIMESTAMP, nullable=False, server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("account_id", "nonce", "message", "recipient"),
    )


def downgrade() -> None:
    op.drop_table("nonces")
