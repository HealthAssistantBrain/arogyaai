"""add feedback table

Revision ID: z9a0b1c2d3e4
Revises: y8z9a0b1c2d3
Create Date: 2026-05-02 23:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "z9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "y8z9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ENTITY_ENUM = ("prediction", "explanation", "recommendation", "anomaly")
FEEDBACK_ENUM = ("correct", "incorrect", "partial", "helpful", "not_helpful")


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if table_name not in _table_names(inspector):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "feedback" in _table_names(inspector):
        return

    entity_enum = postgresql.ENUM(*ENTITY_ENUM, name="feedback_entity_type_enum", create_type=False)
    feedback_enum = postgresql.ENUM(*FEEDBACK_ENUM, name="feedback_type_enum", create_type=False)
    entity_enum.create(bind, checkfirst=True)
    feedback_enum.create(bind, checkfirst=True)

    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", entity_enum, nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("feedback_type", feedback_enum, nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_feedback_rating_1_5"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"], unique=False)
    op.create_index("ix_feedback_entity_type", "feedback", ["entity_type"], unique=False)
    op.create_index("ix_feedback_entity_id", "feedback", ["entity_id"], unique=False)
    op.create_index("ix_feedback_feedback_type", "feedback", ["feedback_type"], unique=False)
    op.create_index("ix_feedback_created_at", "feedback", ["created_at"], unique=False)
    op.create_index("ix_feedback_user_entity", "feedback", ["user_id", "entity_type", "entity_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "feedback" in _table_names(inspector):
        indexes = _index_names(inspector, "feedback")
        for index_name in (
            "ix_feedback_user_entity",
            "ix_feedback_created_at",
            "ix_feedback_feedback_type",
            "ix_feedback_entity_id",
            "ix_feedback_entity_type",
            "ix_feedback_user_id",
        ):
            if index_name in indexes:
                op.drop_index(index_name, table_name="feedback")
        op.drop_table("feedback")

    postgresql.ENUM(name="feedback_type_enum").drop(bind, checkfirst=True)
    postgresql.ENUM(name="feedback_entity_type_enum").drop(bind, checkfirst=True)
