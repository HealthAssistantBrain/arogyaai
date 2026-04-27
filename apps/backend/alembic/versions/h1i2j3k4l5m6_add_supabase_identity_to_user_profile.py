"""add supabase identity columns to user_profile

Revision ID: h1i2j3k4l5m6
Revises: 84585fc132f1
Create Date: 2026-04-27 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "h1i2j3k4l5m6"
down_revision: Union[str, Sequence[str], None] = "84585fc132f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _unique_column_sets(inspector: sa.Inspector, table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(constraint["column_names"] or ())
        for constraint in inspector.get_unique_constraints(table_name)
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "user_profile" not in inspector.get_table_names():
        return

    columns = _column_names(inspector, "user_profile")
    if "supabase_id" not in columns:
        op.add_column(
            "user_profile",
            sa.Column("supabase_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
    if "email" not in columns:
        op.add_column("user_profile", sa.Column("email", sa.Text(), nullable=True))
    if "created_at" not in columns:
        op.add_column(
            "user_profile",
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )

    # Profiles previously created by the direct Supabase bridge used users.id as
    # the Supabase subject. Backfill only those sentinel rows, leaving legacy
    # password users untouched.
    if "users" in inspector.get_table_names():
        bind.execute(
            sa.text(
                """
                UPDATE user_profile AS profile
                SET
                    supabase_id = COALESCE(profile.supabase_id, users.id),
                    email = COALESCE(profile.email, users.email)
                FROM users
                WHERE profile.user_id = users.id
                  AND users.password_hash = 'SUPABASE_AUTH'
                  AND profile.supabase_id IS NULL
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE user_profile AS profile
                SET email = COALESCE(profile.email, users.email)
                FROM users
                WHERE profile.user_id = users.id
                  AND profile.email IS NULL
                """
            )
        )

    inspector = sa.inspect(bind)
    unique_sets = _unique_column_sets(inspector, "user_profile")
    if ("supabase_id",) not in unique_sets:
        op.create_unique_constraint("uq_user_profile_supabase_id", "user_profile", ["supabase_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "user_profile" not in inspector.get_table_names():
        return

    unique_names = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("user_profile")
        if tuple(constraint["column_names"] or ()) == ("supabase_id",)
    }
    for name in unique_names:
        op.drop_constraint(name, "user_profile", type_="unique")

    columns = _column_names(inspector, "user_profile")
    if "email" in columns:
        op.drop_column("user_profile", "email")
    if "supabase_id" in columns:
        op.drop_column("user_profile", "supabase_id")
