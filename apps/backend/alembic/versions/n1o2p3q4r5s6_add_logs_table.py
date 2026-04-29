"""Add logs table

Revision ID: n1o2p3q4r5s6
Revises: m1n2o3p4q5r6
Create Date: 2026-04-30 00:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "n1o2p3q4r5s6"
down_revision: Union[str, Sequence[str], None] = "m1n2o3p4q5r6"
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

    if "logs" not in _table_names(inspector):
        op.create_table(
            "logs",
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("endpoint", sa.String(length=255), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
                server_default=sa.text("gen_random_uuid()"),
            ),
        )

    inspector = sa.inspect(bind)
    indexes = _index_names(inspector, "logs")
    if "ix_logs_user_id" not in indexes:
        op.create_index("ix_logs_user_id", "logs", ["user_id"], unique=False)
    if "ix_logs_created_at" not in indexes:
        op.create_index("ix_logs_created_at", "logs", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "logs" in _table_names(inspector):
        indexes = _index_names(inspector, "logs")
        if "ix_logs_created_at" in indexes:
            op.drop_index("ix_logs_created_at", table_name="logs")
        if "ix_logs_user_id" in indexes:
            op.drop_index("ix_logs_user_id", table_name="logs")
        op.drop_table("logs")
