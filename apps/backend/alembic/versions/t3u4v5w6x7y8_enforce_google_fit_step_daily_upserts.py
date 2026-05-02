"""enforce google fit step daily upserts

Revision ID: t3u4v5w6x7y8
Revises: s2t3u4v5w6x7
Create Date: 2026-05-01 10:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "t3u4v5w6x7y8"
down_revision: Union[str, Sequence[str], None] = "s2t3u4v5w6x7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    if "user_vitals" in tables:
        op.execute(
            sa.text(
                """
                WITH ranked AS (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY user_id, (timestamp AT TIME ZONE 'Asia/Kolkata')::date
                            ORDER BY timestamp DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
                        ) AS row_number
                    FROM user_vitals
                    WHERE type::text IN ('STEPS', 'steps')
                      AND source::text IN ('GOOGLE_FIT', 'google_fit')
                )
                DELETE FROM user_vitals uv
                USING ranked r
                WHERE uv.id = r.id
                  AND r.row_number > 1
                """
            )
        )
        op.execute(
            sa.text(
                """
                WITH ranked AS (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY user_id, type, timestamp, source
                            ORDER BY created_at DESC NULLS LAST, id DESC
                        ) AS row_number
                    FROM user_vitals
                )
                DELETE FROM user_vitals uv
                USING ranked r
                WHERE uv.id = r.id
                  AND r.row_number > 1
                """
            )
        )

        constraint_names = {constraint["name"] for constraint in inspector.get_unique_constraints("user_vitals")}
        if "uq_user_vitals_user_type_timestamp_source" not in constraint_names:
            op.create_unique_constraint(
                "uq_user_vitals_user_type_timestamp_source",
                "user_vitals",
                ["user_id", "type", "timestamp", "source"],
            )

    inspector = sa.inspect(bind)
    tables = _table_names(inspector)
    if "wearable_data" in tables:
        op.execute(
            sa.text(
                """
                WITH ranked AS (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY user_id, (recorded_at AT TIME ZONE 'Asia/Kolkata')::date
                            ORDER BY recorded_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
                        ) AS row_number
                    FROM wearable_data
                    WHERE step_count IS NOT NULL
                )
                DELETE FROM wearable_data wd
                USING ranked r
                WHERE wd.id = r.id
                  AND r.row_number > 1
                """
            )
        )

        index_names = {index["name"] for index in inspector.get_indexes("wearable_data")}
        if "uq_wearable_data_user_recorded_at_steps" not in index_names:
            op.create_index(
                "uq_wearable_data_user_recorded_at_steps",
                "wearable_data",
                ["user_id", "recorded_at"],
                unique=True,
                postgresql_where=sa.text("step_count IS NOT NULL"),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    if "wearable_data" in tables:
        index_names = {index["name"] for index in inspector.get_indexes("wearable_data")}
        if "uq_wearable_data_user_recorded_at_steps" in index_names:
            op.drop_index("uq_wearable_data_user_recorded_at_steps", table_name="wearable_data")

    if "user_vitals" in tables:
        constraint_names = {constraint["name"] for constraint in inspector.get_unique_constraints("user_vitals")}
        if "uq_user_vitals_user_type_timestamp_source" in constraint_names:
            op.drop_constraint("uq_user_vitals_user_type_timestamp_source", "user_vitals", type_="unique")
