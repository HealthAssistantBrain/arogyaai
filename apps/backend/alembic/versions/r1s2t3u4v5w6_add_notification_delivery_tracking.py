"""add notification delivery tracking

Revision ID: r1s2t3u4v5w6
Revises: p2q3r4s5t6u7
Create Date: 2026-04-30 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "r1s2t3u4v5w6"
down_revision: Union[str, Sequence[str], None] = "p2q3r4s5t6u7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.execute("ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'simulation'")

    if "notifications" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("notifications")}
    indexes = {index["name"] for index in inspector.get_indexes("notifications")}

    if "delivery_status" not in columns:
        op.add_column("notifications", sa.Column("delivery_status", sa.String(length=32), nullable=False, server_default="pending"))
    if "email_status" not in columns:
        op.add_column("notifications", sa.Column("email_status", sa.String(length=32), nullable=False, server_default="disabled"))
    if "push_status" not in columns:
        op.add_column("notifications", sa.Column("push_status", sa.String(length=32), nullable=False, server_default="disabled"))
    if "delivery_attempts" not in columns:
        op.add_column("notifications", sa.Column("delivery_attempts", sa.Integer(), nullable=False, server_default="0"))
    if "last_delivery_error" not in columns:
        op.add_column("notifications", sa.Column("last_delivery_error", sa.Text(), nullable=True))
    if "queued_at" not in columns:
        op.add_column("notifications", sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True))
    if "processed_at" not in columns:
        op.add_column("notifications", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))
    if "delivered_at" not in columns:
        op.add_column("notifications", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))

    delivery_status_index = op.f("ix_notifications_delivery_status")
    if delivery_status_index not in indexes:
        op.create_index(delivery_status_index, "notifications", ["delivery_status"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "notifications" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("notifications")}
    indexes = {index["name"] for index in inspector.get_indexes("notifications")}
    delivery_status_index = op.f("ix_notifications_delivery_status")

    if delivery_status_index in indexes:
        op.drop_index(delivery_status_index, table_name="notifications")
    if "delivered_at" in columns:
        op.drop_column("notifications", "delivered_at")
    if "processed_at" in columns:
        op.drop_column("notifications", "processed_at")
    if "queued_at" in columns:
        op.drop_column("notifications", "queued_at")
    if "last_delivery_error" in columns:
        op.drop_column("notifications", "last_delivery_error")
    if "delivery_attempts" in columns:
        op.drop_column("notifications", "delivery_attempts")
    if "push_status" in columns:
        op.drop_column("notifications", "push_status")
    if "email_status" in columns:
        op.drop_column("notifications", "email_status")
    if "delivery_status" in columns:
        op.drop_column("notifications", "delivery_status")

    # PostgreSQL enum values cannot be removed safely in downgrade without recreating dependent objects.
