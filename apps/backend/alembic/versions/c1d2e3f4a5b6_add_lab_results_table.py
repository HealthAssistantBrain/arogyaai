"""add lab_results table

Revision ID: c1d2e3f4a5b6
Revises: b8c1d4f7a9e2
Create Date: 2026-04-14 21:23:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b8c1d4f7a9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lab_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("reference_range", sa.String(100), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        if_not_exists=True,
    )
    # Indexes for common query patterns
    op.create_index("ix_lab_results_user_id", "lab_results", ["user_id"], if_not_exists=True)
    op.create_index("ix_lab_results_report_id", "lab_results", ["report_id"], if_not_exists=True)
    op.create_index("ix_lab_results_category", "lab_results", ["category"], if_not_exists=True)
    op.create_index("ix_lab_results_timestamp", "lab_results", ["timestamp"], if_not_exists=True)
    # Unique constraint enables ON CONFLICT DO UPDATE upsert per (user, report, parameter)
    op.create_index(
        "uq_lab_results_user_report_name",
        "lab_results",
        ["user_id", "report_id", "name"],
        unique=True,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_lab_results_timestamp", table_name="lab_results", if_exists=True)
    op.drop_index("ix_lab_results_category", table_name="lab_results", if_exists=True)
    op.drop_index("ix_lab_results_report_id", table_name="lab_results", if_exists=True)
    op.drop_index("ix_lab_results_user_id", table_name="lab_results", if_exists=True)
    op.drop_table("lab_results", if_exists=True)
