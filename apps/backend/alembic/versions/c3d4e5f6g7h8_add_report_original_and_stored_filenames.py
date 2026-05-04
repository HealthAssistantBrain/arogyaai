"""Add original and stored filenames to reports

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-05-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("reports")}

    if "original_filename" not in existing_columns:
        op.add_column(
            "reports",
            sa.Column("original_filename", sa.Text(), nullable=True, comment="Original filename supplied by the user"),
        )

    if "stored_filename" not in existing_columns:
        op.add_column(
            "reports",
            sa.Column("stored_filename", sa.Text(), nullable=True, comment="Internal storage object filename"),
        )

    op.execute(
        """
        UPDATE reports
        SET
            original_filename = COALESCE(
                original_filename,
                summary_data #>> '{upload_metadata,original_filename}',
                summary_data #>> '{upload_metadata,file_name}'
            ),
            stored_filename = COALESCE(
                stored_filename,
                NULLIF(regexp_replace(COALESCE(storage_path, file_url, ''), '^.*/', ''), '')
            )
        WHERE original_filename IS NULL
           OR stored_filename IS NULL
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("reports")}

    if "stored_filename" in existing_columns:
        op.drop_column("reports", "stored_filename")
    if "original_filename" in existing_columns:
        op.drop_column("reports", "original_filename")
