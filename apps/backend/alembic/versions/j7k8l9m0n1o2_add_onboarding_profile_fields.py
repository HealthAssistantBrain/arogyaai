"""add onboarding profile fields to user_profile

Revision ID: j7k8l9m0n1o2
Revises: h1i2j3k4l5m6
Create Date: 2026-04-27 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j7k8l9m0n1o2"
down_revision: Union[str, Sequence[str], None] = "h1i2j3k4l5m6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "user_profile" not in inspector.get_table_names():
        return

    columns = _column_names(inspector, "user_profile")

    if "age" not in columns:
        op.add_column("user_profile", sa.Column("age", sa.Integer(), nullable=True))
    if "activity_level" not in columns:
        op.add_column("user_profile", sa.Column("activity_level", sa.Integer(), nullable=True))
    if "goals" not in columns:
        op.add_column("user_profile", sa.Column("goals", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "user_profile" not in inspector.get_table_names():
        return

    columns = _column_names(inspector, "user_profile")

    if "goals" in columns:
        op.drop_column("user_profile", "goals")
    if "activity_level" in columns:
        op.drop_column("user_profile", "activity_level")
    if "age" in columns:
        op.drop_column("user_profile", "age")
