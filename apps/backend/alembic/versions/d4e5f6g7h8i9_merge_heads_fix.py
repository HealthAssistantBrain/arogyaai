"""merge heads fix

Revision ID: d4e5f6g7h8i9
Revises: a0b1c2d3e4f5, c3d4e5f6g7h8
Create Date: 2026-05-04 16:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, Sequence[str], None] = ("a0b1c2d3e4f5", "c3d4e5f6g7h8")
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
    tables = _table_names(inspector)

    if "reports" not in tables or "timeline_events" not in tables:
        return

    report_columns = _column_names(inspector, "reports")
    required_columns = {
        "id",
        "user_id",
        "created_at",
        "original_filename",
        "stored_filename",
        "file_url",
        "report_type",
        "status",
        "is_deleted",
    }
    if not required_columns.issubset(report_columns):
        return

    op.execute(
        sa.text(
            """
            INSERT INTO timeline_events (user_id, type, title, reference_id, timestamp, metadata)
            SELECT
                r.user_id,
                'report',
                'Medical report uploaded',
                r.id,
                COALESCE(r.created_at, now()),
                jsonb_build_object(
                    'report_id', r.id::text,
                    'filename', COALESCE(r.original_filename, r.stored_filename, 'Medical report'),
                    'original_filename', r.original_filename,
                    'stored_filename', r.stored_filename,
                    'file_url', r.file_url,
                    'report_type', r.report_type::text,
                    'status', r.status::text,
                    'source', 'report upload',
                    'url', '/medical-reports'
                )
            FROM reports r
            WHERE COALESCE(r.is_deleted, false) = false
            ON CONFLICT (user_id, type, reference_id) DO UPDATE
            SET
                title = EXCLUDED.title,
                timestamp = EXCLUDED.timestamp,
                metadata = timeline_events.metadata || EXCLUDED.metadata,
                updated_at = now()
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = _table_names(inspector)
    if "timeline_events" not in tables:
        return

    timeline_columns = _column_names(inspector, "timeline_events")
    if {"type", "metadata"}.issubset(timeline_columns):
        op.execute(
            sa.text(
                """
                DELETE FROM timeline_events
                WHERE type = 'report'
                  AND metadata ->> 'source' = 'report upload'
                """
            )
        )
