"""extend onboarding profile intake fields

Revision ID: q8r9s0t1u2v3
Revises: j7k8l9m0n1o2
Create Date: 2026-04-30 23:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q8r9s0t1u2v3"
down_revision: Union[str, Sequence[str], None] = "j7k8l9m0n1o2"
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
    additions = {
        "occupation": sa.Column("occupation", sa.String(length=150), nullable=True),
        "city": sa.Column("city", sa.String(length=120), nullable=True),
        "marital_status": sa.Column("marital_status", sa.String(length=50), nullable=True),
        "family_history": sa.Column("family_history", sa.Text(), nullable=True),
        "surgeries": sa.Column("surgeries", sa.Text(), nullable=True),
        "hospitalizations": sa.Column("hospitalizations", sa.Boolean(), nullable=True),
        "hospitalization_details": sa.Column("hospitalization_details", sa.Text(), nullable=True),
        "current_medications": sa.Column("current_medications", sa.Text(), nullable=True),
        "sleep_hours": sa.Column("sleep_hours", sa.Numeric(4, 1), nullable=True),
        "stress_level": sa.Column("stress_level", sa.Integer(), nullable=True),
        "smoking": sa.Column("smoking", sa.Boolean(), nullable=True),
        "alcohol": sa.Column("alcohol", sa.Boolean(), nullable=True),
        "appetite": sa.Column("appetite", sa.String(length=20), nullable=True),
        "bowel_habits": sa.Column("bowel_habits", sa.String(length=20), nullable=True),
    }

    for name, column in additions.items():
        if name not in columns:
            op.add_column("user_profile", column)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "user_profile" not in inspector.get_table_names():
        return

    columns = _column_names(inspector, "user_profile")
    for name in (
        "bowel_habits",
        "appetite",
        "alcohol",
        "smoking",
        "stress_level",
        "sleep_hours",
        "current_medications",
        "hospitalization_details",
        "hospitalizations",
        "surgeries",
        "family_history",
        "marital_status",
        "city",
        "occupation",
    ):
        if name in columns:
            op.drop_column("user_profile", name)
