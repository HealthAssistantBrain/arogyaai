"""add notification metadata and activity type

Revision ID: 7f1a9d2b3c4e
Revises: 2d3c4e5f6a7b
Create Date: 2026-04-06 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "7f1a9d2b3c4e"
down_revision: Union[str, Sequence[str], None] = "2d3c4e5f6a7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "notifications" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("notifications")}
        if "metadata" not in columns:
            op.add_column(
                "notifications",
                sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            )

    op.execute("ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'activity'")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "notifications" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("notifications")}
        if "metadata" in columns:
            op.drop_column("notifications", "metadata")

    # PostgreSQL enum values cannot be removed safely in downgrade without recreating dependent objects.
