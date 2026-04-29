"""Ensure alerts table exists

Revision ID: m1n2o3p4q5r6
Revises: k1l2m3n4o5p6
Create Date: 2026-04-30 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m1n2o3p4q5r6"
down_revision: Union[str, Sequence[str], None] = "k1l2m3n4o5p6"
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

    with op.get_context().autocommit_block():
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_type_enum') THEN
                    CREATE TYPE alert_type_enum AS ENUM (
                        'VITAL_ANOMALY',
                        'REPORT_READY',
                        'SYSTEM_UPDATE',
                        'REMINDER',
                        'SECURITY'
                    );
                END IF;
            END
            $$;
            """
        )
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'severity_enum') THEN
                    CREATE TYPE severity_enum AS ENUM ('INFO', 'WARNING', 'CRITICAL');
                END IF;
            END
            $$;
            """
        )

    if "alerts" not in _table_names(inspector):
        op.create_table(
            "alerts",
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "alert_type",
                postgresql.ENUM(
                    "VITAL_ANOMALY",
                    "REPORT_READY",
                    "SYSTEM_UPDATE",
                    "REMINDER",
                    "SECURITY",
                    name="alert_type_enum",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "severity",
                postgresql.ENUM(
                    "INFO",
                    "WARNING",
                    "CRITICAL",
                    name="severity_enum",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("is_read", sa.Boolean(), nullable=True, server_default=sa.text("false")),
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
    indexes = _index_names(inspector, "alerts")
    if "ix_alerts_user_id" not in indexes:
        op.create_index("ix_alerts_user_id", "alerts", ["user_id"], unique=False)
    if "ix_alerts_severity" not in indexes:
        op.create_index("ix_alerts_severity", "alerts", ["severity"], unique=False)
    if "ix_alerts_is_read" not in indexes:
        op.create_index("ix_alerts_is_read", "alerts", ["is_read"], unique=False)
    if "ix_alerts_created_at" not in indexes:
        op.create_index("ix_alerts_created_at", "alerts", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "alerts" in _table_names(inspector):
        indexes = _index_names(inspector, "alerts")
        if "ix_alerts_created_at" in indexes:
            op.drop_index("ix_alerts_created_at", table_name="alerts")
        if "ix_alerts_is_read" in indexes:
            op.drop_index("ix_alerts_is_read", table_name="alerts")
        if "ix_alerts_severity" in indexes:
            op.drop_index("ix_alerts_severity", table_name="alerts")
        if "ix_alerts_user_id" in indexes:
            op.drop_index("ix_alerts_user_id", table_name="alerts")
        op.drop_table("alerts")

    with op.get_context().autocommit_block():
        op.execute("DROP TYPE IF EXISTS severity_enum")
        op.execute("DROP TYPE IF EXISTS alert_type_enum")
