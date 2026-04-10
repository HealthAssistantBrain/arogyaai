"""Add phone_DOB_gender

Revision ID: 74ab73e1a50a
Revises: add_user_profile_table
Create Date: 2026-04-06 10:34:48.367501

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74ab73e1a50a'
down_revision: Union[str, Sequence[str], None] = 'add_user_profile_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "user_profile" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("user_profile")}

    if "phone" not in existing_columns and "phone_number" not in existing_columns:
        op.add_column("user_profile", sa.Column("phone", sa.String(length=20), nullable=True))
    if "date_of_birth" not in existing_columns:
        op.add_column("user_profile", sa.Column("date_of_birth", sa.Date(), nullable=True))
    if "gender" not in existing_columns:
        op.add_column("user_profile", sa.Column("gender", sa.String(length=20), nullable=True))

    unique_constraints = {tuple(constraint["column_names"]) for constraint in inspector.get_unique_constraints("user_profile")}
    if ("user_id",) in unique_constraints:
        op.drop_constraint(op.f("user_profile_user_id_key"), "user_profile", type_="unique")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "user_profile" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("user_profile")}

    unique_constraints = {tuple(constraint["column_names"]) for constraint in inspector.get_unique_constraints("user_profile")}
    if ("user_id",) not in unique_constraints:
        op.create_unique_constraint(op.f("user_profile_user_id_key"), "user_profile", ["user_id"], postgresql_nulls_not_distinct=False)

    if "gender" in existing_columns:
        op.drop_column("user_profile", "gender")
    if "date_of_birth" in existing_columns:
        op.drop_column("user_profile", "date_of_birth")
    if "phone" in existing_columns:
        op.drop_column("user_profile", "phone")
