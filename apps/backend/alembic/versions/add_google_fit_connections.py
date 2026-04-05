"""add google fit connections

Revision ID: add_google_fit_connections
Revises: add_health_score_columns
Create Date: 2026-04-05 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "add_google_fit_connections"
down_revision: Union[str, Sequence[str], None] = "add_health_score_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "google_fit_connections" not in inspector.get_table_names():
        op.create_table(
            "google_fit_connections",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("google_email", sa.String(length=255), nullable=True),
            sa.Column("scopes", sa.Text(), nullable=True),
            sa.Column("default_timezone", sa.String(length=64), nullable=False, server_default="Asia/Kolkata"),
            sa.Column("access_token_encrypted", sa.Text(), nullable=True),
            sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
            sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_sync_status", sa.String(length=50), nullable=True),
            sa.Column("raw_last_response", sa.JSON(), nullable=True),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("google_fit_connections")}
    device_index = op.f("ix_google_fit_connections_device_id")
    user_index = op.f("ix_google_fit_connections_user_id")

    if device_index not in existing_indexes:
        op.create_index(device_index, "google_fit_connections", ["device_id"], unique=False)
    if user_index not in existing_indexes:
        op.create_index(user_index, "google_fit_connections", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_google_fit_connections_user_id"), table_name="google_fit_connections")
    op.drop_index(op.f("ix_google_fit_connections_device_id"), table_name="google_fit_connections")
    op.drop_table("google_fit_connections")
