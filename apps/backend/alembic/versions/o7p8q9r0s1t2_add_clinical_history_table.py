"""add clinical history table

Revision ID: o7p8q9r0s1t2
Revises: n1o2p3q4r5s6
Create Date: 2026-04-30 12:40:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "o7p8q9r0s1t2"
down_revision: Union[str, Sequence[str], None] = "n1o2p3q4r5s6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if table_name not in _table_names(inspector):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "clinical_history" not in _table_names(inspector):
        op.create_table(
            "clinical_history",
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("chief_complaint", sa.Text(), nullable=True),
            sa.Column("duration", sa.Text(), nullable=True),
            sa.Column("onset", sa.Text(), nullable=True),
            sa.Column("severity", sa.Integer(), nullable=True),
            sa.Column("associated_symptoms", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("negative_symptoms", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("aggravating_factors", sa.Text(), nullable=True),
            sa.Column("relieving_factors", sa.Text(), nullable=True),
            sa.Column("past_history", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
                server_default=sa.text("gen_random_uuid()"),
            ),
        )

    inspector = sa.inspect(bind)
    indexes = _index_names(inspector, "clinical_history")
    if "ix_clinical_history_user_id" not in indexes:
        op.create_index("ix_clinical_history_user_id", "clinical_history", ["user_id"], unique=False)
    if "ix_clinical_history_created_at" not in indexes:
        op.create_index("ix_clinical_history_created_at", "clinical_history", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "clinical_history" in _table_names(inspector):
        indexes = _index_names(inspector, "clinical_history")
        if "ix_clinical_history_created_at" in indexes:
            op.drop_index("ix_clinical_history_created_at", table_name="clinical_history")
        if "ix_clinical_history_user_id" in indexes:
            op.drop_index("ix_clinical_history_user_id", table_name="clinical_history")
        op.drop_table("clinical_history")
