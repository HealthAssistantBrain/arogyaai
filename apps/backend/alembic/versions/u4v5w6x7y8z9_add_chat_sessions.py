"""add chat sessions

Revision ID: u4v5w6x7y8z9
Revises: t3u4v5w6x7y8
Create Date: 2026-05-01 17:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "u4v5w6x7y8z9"
down_revision: Union[str, Sequence[str], None] = "t3u4v5w6x7y8"
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

    if "chat_sessions" not in _table_names(inspector):
        op.create_table(
            "chat_sessions",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("messages", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("symptoms_history", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("last_risk_score", sa.Float(), nullable=True),
            sa.Column("follow_up_pending", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chat_sessions_user_id_users", ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", name="uq_chat_sessions_user_id"),
        )

    inspector = sa.inspect(bind)
    indexes = _index_names(inspector, "chat_sessions")
    if "ix_chat_sessions_user_id" not in indexes:
        op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "chat_sessions" in _table_names(inspector):
        indexes = _index_names(inspector, "chat_sessions")
        if "ix_chat_sessions_user_id" in indexes:
            op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
        op.drop_table("chat_sessions")
