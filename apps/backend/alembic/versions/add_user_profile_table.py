"""add user_profile table

Revision ID: add_user_profile_table
Revises: add_google_fit_connections
Create Date: 2026-04-06 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "add_user_profile_table"
down_revision: Union[str, Sequence[str], None] = "add_google_fit_connections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "user_profile" not in inspector.get_table_names():
        op.create_table(
            "user_profile",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("full_name", sa.String(length=150), nullable=True),
            sa.Column("avatar_url", sa.Text(), nullable=True),
            sa.Column("height", sa.Numeric(5, 2), nullable=True),
            sa.Column("weight", sa.Numeric(5, 2), nullable=True),
            sa.Column("blood_group", sa.String(length=5), nullable=True),
            sa.Column("allergies", sa.Text(), nullable=True),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("user_profile")}
    user_index = op.f("ix_user_profile_user_id")
    if user_index not in existing_indexes:
        op.create_index(user_index, "user_profile", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_profile_user_id"), table_name="user_profile")
    op.drop_table("user_profile")
