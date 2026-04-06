"""add notifications table

Revision ID: 9b6c1f2a7d4e
Revises: 74ab73e1a50a
Create Date: 2026-04-06 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9b6c1f2a7d4e"
down_revision: Union[str, Sequence[str], None] = "74ab73e1a50a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "notifications" not in inspector.get_table_names():
        op.create_table(
            "notifications",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("type", sa.Enum("ai_insight", "health_alert", "appointment", "system", name="notification_type_enum"), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("severity", sa.Enum("info", "warning", "critical", name="notification_severity_enum"), nullable=False),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("notifications")} if "notifications" in inspector.get_table_names() else set()

    user_index = op.f("ix_notifications_user_id")
    type_index = op.f("ix_notifications_type")
    severity_index = op.f("ix_notifications_severity")
    is_read_index = op.f("ix_notifications_is_read")
    created_index = op.f("ix_notifications_created_at")

    if user_index not in existing_indexes:
        op.create_index(user_index, "notifications", ["user_id"], unique=False)
    if type_index not in existing_indexes:
        op.create_index(type_index, "notifications", ["type"], unique=False)
    if severity_index not in existing_indexes:
        op.create_index(severity_index, "notifications", ["severity"], unique=False)
    if is_read_index not in existing_indexes:
        op.create_index(is_read_index, "notifications", ["is_read"], unique=False)
    if created_index not in existing_indexes:
        op.create_index(created_index, "notifications", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_created_at"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_is_read"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_severity"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_type"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_table("notifications")
    op.execute("DROP TYPE IF EXISTS notification_severity_enum")
    op.execute("DROP TYPE IF EXISTS notification_type_enum")
