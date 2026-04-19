"""add social connection flags to users

Revision ID: 9a8b7c6d5e4f
Revises: f1a2b3c4d5e6
Create Date: 2026-04-18 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "gmail_connected" not in columns:
        op.add_column(
            "users",
            sa.Column("gmail_connected", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    if "apple_connected" not in columns:
        op.add_column(
            "users",
            sa.Column("apple_connected", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    op.drop_column("users", "apple_connected")
    op.drop_column("users", "gmail_connected")
