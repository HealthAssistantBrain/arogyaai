"""add recommendation snapshots table

Revision ID: p9q0r1s2t3u4
Revises: n7o8p9q0r1s2
Create Date: 2026-05-12 12:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p9q0r1s2t3u4"
down_revision: Union[str, Sequence[str], None] = "n7o8p9q0r1s2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "recommendation_snapshots" in inspector.get_table_names():
        return

    op.create_table(
        "recommendation_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("cache_key", sa.Text(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prediction_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key"),
    )
    op.create_index("ix_recommendation_snapshots_cache_key", "recommendation_snapshots", ["cache_key"], unique=False)
    op.create_index("ix_recommendation_snapshots_expires_at", "recommendation_snapshots", ["expires_at"], unique=False)
    op.create_index("ix_recommendation_snapshots_prediction_id", "recommendation_snapshots", ["prediction_id"], unique=False)
    op.create_index("ix_recommendation_snapshots_user_id", "recommendation_snapshots", ["user_id"], unique=False)
    op.create_index(
        "ix_recommendation_snapshots_user_updated",
        "recommendation_snapshots",
        ["user_id", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_recommendation_snapshots_user_updated", table_name="recommendation_snapshots")
    op.drop_index("ix_recommendation_snapshots_user_id", table_name="recommendation_snapshots")
    op.drop_index("ix_recommendation_snapshots_prediction_id", table_name="recommendation_snapshots")
    op.drop_index("ix_recommendation_snapshots_expires_at", table_name="recommendation_snapshots")
    op.drop_index("ix_recommendation_snapshots_cache_key", table_name="recommendation_snapshots")
    op.drop_table("recommendation_snapshots")
