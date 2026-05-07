"""add raw and normalized vital value fields

Revision ID: g8h9i0j1k2l3
Revises: f6g7h8i9j0k1
Create Date: 2026-05-06 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "g8h9i0j1k2l3"
down_revision: Union[str, Sequence[str], None] = "f6g7h8i9j0k1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "user_vitals" not in tables:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("user_vitals")}

    if "raw_value" not in existing_columns:
        op.add_column("user_vitals", sa.Column("raw_value", sa.Float(), nullable=True))
    if "raw_unit" not in existing_columns:
        op.add_column("user_vitals", sa.Column("raw_unit", sa.String(length=20), nullable=True))
    if "normalized_value" not in existing_columns:
        op.add_column("user_vitals", sa.Column("normalized_value", sa.Float(), nullable=True))
    if "normalized_unit" not in existing_columns:
        op.add_column("user_vitals", sa.Column("normalized_unit", sa.String(length=20), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE user_vitals
               SET raw_value = COALESCE(raw_value, value),
                   raw_unit = COALESCE(NULLIF(raw_unit, ''), unit),
                   normalized_value = COALESCE(normalized_value, value),
                   normalized_unit = COALESCE(NULLIF(normalized_unit, ''), unit)
             WHERE raw_value IS NULL
                OR raw_unit IS NULL
                OR normalized_value IS NULL
                OR normalized_unit IS NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "user_vitals" not in tables:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("user_vitals")}

    if "normalized_unit" in existing_columns:
        op.drop_column("user_vitals", "normalized_unit")
    if "normalized_value" in existing_columns:
        op.drop_column("user_vitals", "normalized_value")
    if "raw_unit" in existing_columns:
        op.drop_column("user_vitals", "raw_unit")
    if "raw_value" in existing_columns:
        op.drop_column("user_vitals", "raw_value")
