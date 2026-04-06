"""Add health_score and score_change_percent to users

Revision ID: add_health_score_columns
Revises: 4dee8928dc66
Create Date: 2026-04-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_health_score_columns'
down_revision: Union[str, Sequence[str], None] = '4dee8928dc66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    if "health_score" not in existing_columns:
        op.add_column("users", sa.Column("health_score", sa.Numeric(5, 2), nullable=True, server_default="0.0"))
    if "score_change_percent" not in existing_columns:
        op.add_column("users", sa.Column("score_change_percent", sa.Numeric(5, 2), nullable=True, server_default="0.0"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    if "score_change_percent" in existing_columns:
        op.drop_column("users", "score_change_percent")
    if "health_score" in existing_columns:
        op.drop_column("users", "health_score")
