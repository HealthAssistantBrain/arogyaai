"""add timeline events table

Revision ID: a0b1c2d3e4f5
Revises: z9a0b1c2d3e4
Create Date: 2026-05-04 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "z9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if table_name not in _table_names(inspector):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _constraint_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if table_name not in _table_names(inspector):
        return set()
    return {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "timeline_events" not in _table_names(inspector):
        op.create_table(
            "timeline_events",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "type", "reference_id", name="uq_timeline_events_user_type_reference"),
        )

    inspector = sa.inspect(bind)
    indexes = _index_names(inspector, "timeline_events")
    if "ix_timeline_events_user_id" not in indexes:
        op.create_index("ix_timeline_events_user_id", "timeline_events", ["user_id"], unique=False)
    if "ix_timeline_events_type" not in indexes:
        op.create_index("ix_timeline_events_type", "timeline_events", ["type"], unique=False)
    if "ix_timeline_events_reference_id" not in indexes:
        op.create_index("ix_timeline_events_reference_id", "timeline_events", ["reference_id"], unique=False)
    if "ix_timeline_events_timestamp" not in indexes:
        op.create_index("ix_timeline_events_timestamp", "timeline_events", ["timestamp"], unique=False)
    if "ix_timeline_events_user_timestamp" not in indexes:
        op.create_index("ix_timeline_events_user_timestamp", "timeline_events", ["user_id", "timestamp"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "timeline_events" not in _table_names(inspector):
        return

    indexes = _index_names(inspector, "timeline_events")
    for index_name in (
        "ix_timeline_events_user_timestamp",
        "ix_timeline_events_timestamp",
        "ix_timeline_events_reference_id",
        "ix_timeline_events_type",
        "ix_timeline_events_user_id",
    ):
        if index_name in indexes:
            op.drop_index(index_name, table_name="timeline_events")

    constraints = _constraint_names(inspector, "timeline_events")
    if "uq_timeline_events_user_type_reference" in constraints:
        op.drop_constraint("uq_timeline_events_user_type_reference", "timeline_events", type_="unique")

    op.drop_table("timeline_events")
