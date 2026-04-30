"""add notification settings and devices

Revision ID: p2q3r4s5t6u7
Revises: o7p8q9r0s1t2
Create Date: 2026-04-30 15:10:00.000000
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "p2q3r4s5t6u7"
down_revision: Union[str, Sequence[str], None] = "o7p8q9r0s1t2"
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
    now = datetime.now(timezone.utc)

    if "notification_preferences" not in _table_names(inspector):
        op.create_table(
            "notification_preferences",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("ai_insights_email", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("ai_insights_push", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("health_alerts_email", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("health_alerts_push", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("reminders_email", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("reminders_push", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
        )

    if "notification_devices" not in _table_names(inspector):
        op.create_table(
            "notification_devices",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("device_token", sa.Text(), nullable=False),
            sa.Column("device_name", sa.String(length=120), nullable=True),
            sa.Column("platform", sa.String(length=50), nullable=False, server_default="web"),
            sa.Column("subscription", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("last_active", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.UniqueConstraint("device_token", name="uq_notification_devices_device_token"),
        )

    inspector = sa.inspect(bind)

    notification_pref_indexes = _index_names(inspector, "notification_preferences")
    if "ix_notification_preferences_user_id" not in notification_pref_indexes:
        op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"], unique=False)

    notification_device_indexes = _index_names(inspector, "notification_devices")
    if "ix_notification_devices_user_id" not in notification_device_indexes:
        op.create_index("ix_notification_devices_user_id", "notification_devices", ["user_id"], unique=False)
    if "ix_notification_devices_last_active" not in notification_device_indexes:
        op.create_index("ix_notification_devices_last_active", "notification_devices", ["last_active"], unique=False)

    if "notification_preferences" in _table_names(inspector) and "users" in _table_names(inspector):
        existing_user_ids = {
            row["user_id"]
            for row in bind.execute(sa.text("SELECT user_id FROM notification_preferences")).mappings().all()
        }
        missing_rows = [
            {
                "id": uuid.uuid4(),
                "user_id": row["id"],
                "email_enabled": True,
                "push_enabled": True,
                "ai_insights_email": True,
                "ai_insights_push": True,
                "health_alerts_email": True,
                "health_alerts_push": True,
                "reminders_email": True,
                "reminders_push": True,
                "updated_at": now,
            }
            for row in bind.execute(sa.text("SELECT id FROM users WHERE is_deleted = false")).mappings().all()
            if row["id"] not in existing_user_ids
        ]
        if missing_rows:
            op.bulk_insert(
                sa.table(
                    "notification_preferences",
                    sa.column("id", postgresql.UUID(as_uuid=True)),
                    sa.column("user_id", postgresql.UUID(as_uuid=True)),
                    sa.column("email_enabled", sa.Boolean()),
                    sa.column("push_enabled", sa.Boolean()),
                    sa.column("ai_insights_email", sa.Boolean()),
                    sa.column("ai_insights_push", sa.Boolean()),
                    sa.column("health_alerts_email", sa.Boolean()),
                    sa.column("health_alerts_push", sa.Boolean()),
                    sa.column("reminders_email", sa.Boolean()),
                    sa.column("reminders_push", sa.Boolean()),
                    sa.column("updated_at", sa.DateTime(timezone=True)),
                ),
                missing_rows,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "notification_devices" in _table_names(inspector):
        indexes = _index_names(inspector, "notification_devices")
        if "ix_notification_devices_last_active" in indexes:
            op.drop_index("ix_notification_devices_last_active", table_name="notification_devices")
        if "ix_notification_devices_user_id" in indexes:
            op.drop_index("ix_notification_devices_user_id", table_name="notification_devices")
        op.drop_table("notification_devices")

    if "notification_preferences" in _table_names(inspector):
        indexes = _index_names(inspector, "notification_preferences")
        if "ix_notification_preferences_user_id" in indexes:
            op.drop_index("ix_notification_preferences_user_id", table_name="notification_preferences")
        op.drop_table("notification_preferences")
