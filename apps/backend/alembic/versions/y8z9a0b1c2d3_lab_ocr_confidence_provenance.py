"""add lab OCR confidence and provenance columns

Revision ID: y8z9a0b1c2d3
Revises: x7y8z9a0b1c2
Create Date: 2026-05-02 04:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "y8z9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "x7y8z9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if table_name not in _table_names(inspector):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _column_names(inspector, "lab_results")
    if not columns:
        return

    if "confidence_score" not in columns:
        op.add_column("lab_results", sa.Column("confidence_score", sa.Float(), nullable=True))
    if "source_span" not in columns:
        op.add_column("lab_results", sa.Column("source_span", sa.Text(), nullable=True))
    if "source_text" not in columns:
        op.add_column("lab_results", sa.Column("source_text", sa.Text(), nullable=True))
    if "source_type" not in columns:
        op.add_column("lab_results", sa.Column("source_type", sa.String(length=30), nullable=True))
    if "page_number" not in columns:
        op.add_column("lab_results", sa.Column("page_number", sa.Integer(), nullable=True))
    if "extraction_method" not in columns:
        op.add_column("lab_results", sa.Column("extraction_method", sa.String(length=50), nullable=True))

    op.execute("UPDATE lab_results SET confidence_score = 0.75 WHERE confidence_score IS NULL;")
    op.execute("UPDATE lab_results SET source_text = source_span WHERE source_text IS NULL AND source_span IS NOT NULL;")
    op.execute("UPDATE lab_results SET source_type = 'PDF' WHERE source_type IS NULL;")
    op.execute("UPDATE lab_results SET page_number = 1 WHERE page_number IS NULL;")
    op.execute("UPDATE lab_results SET extraction_method = 'legacy_import' WHERE extraction_method IS NULL;")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _column_names(inspector, "lab_results")
    if not columns:
        return

    if "extraction_method" in columns:
        op.drop_column("lab_results", "extraction_method")
    if "page_number" in columns:
        op.drop_column("lab_results", "page_number")
    if "source_type" in columns:
        op.drop_column("lab_results", "source_type")
    if "source_text" in columns:
        op.drop_column("lab_results", "source_text")
    if "source_span" in columns:
        op.drop_column("lab_results", "source_span")
    if "confidence_score" in columns:
        op.drop_column("lab_results", "confidence_score")
