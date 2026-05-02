"""add user role for doctor access

Revision ID: w6x7y8z9a0b1
Revises: v5w6x7y8z9a0
Create Date: 2026-05-02 02:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "w6x7y8z9a0b1"
down_revision: Union[str, Sequence[str], None] = "v5w6x7y8z9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    indexes = {index["name"] for index in inspector.get_indexes("users")}

    if "role" not in columns:
        op.add_column(
            "users",
            sa.Column("role", sa.String(length=32), nullable=False, server_default="patient"),
        )

    if "ix_users_role" not in indexes:
        op.create_index("ix_users_role", "users", ["role"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    indexes = {index["name"] for index in inspector.get_indexes("users")}

    if "ix_users_role" in indexes:
        op.drop_index("ix_users_role", table_name="users")
    if "role" in columns:
        op.drop_column("users", "role")
