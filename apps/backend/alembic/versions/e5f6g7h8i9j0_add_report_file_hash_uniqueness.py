"""add report file hash uniqueness

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-05-05 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "e5f6g7h8i9j0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6g7h8i9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("reports")}
    indexes = {index["name"] for index in inspector.get_indexes("reports")}
    constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("reports")
        if constraint.get("name")
    }

    if "file_hash" not in columns:
        op.add_column("reports", sa.Column("file_hash", sa.String(length=64), nullable=True))

    if "ix_reports_file_hash" not in indexes:
        op.create_index("ix_reports_file_hash", "reports", ["file_hash"], unique=False)

    if "uq_reports_user_file_hash" not in constraints:
        op.create_unique_constraint("uq_reports_user_file_hash", "reports", ["user_id", "file_hash"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("reports")}
    constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("reports")
        if constraint.get("name")
    }
    columns = {column["name"] for column in inspector.get_columns("reports")}

    if "uq_reports_user_file_hash" in constraints:
        op.drop_constraint("uq_reports_user_file_hash", "reports", type_="unique")

    if "ix_reports_file_hash" in indexes:
        op.drop_index("ix_reports_file_hash", table_name="reports")

    if "file_hash" in columns:
        op.drop_column("reports", "file_hash")
