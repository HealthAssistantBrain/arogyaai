"""add wearable metrics google fit metrics

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-04 10:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name) if index.get("name")}


def _unique_constraint_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name) if constraint.get("name")}


def _add_enum_value(enum_name: str, value: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}')
               AND NOT EXISTS (
                   SELECT 1
                   FROM pg_enum e
                   JOIN pg_type t ON t.oid = e.enumtypid
                   WHERE t.typname = '{enum_name}'
                     AND e.enumlabel = '{value}'
               )
            THEN
                ALTER TYPE {enum_name} ADD VALUE '{value}';
            END IF;
        END $$;
        """
    )


def _has_hypertable(bind, table_name: str) -> bool:
    try:
        return bool(
            bind.execute(
                sa.text(
                    """
                    SELECT 1
                    FROM timescaledb_information.hypertables
                    WHERE hypertable_schema = current_schema()
                      AND hypertable_name = :table_name
                    """
                ),
                {"table_name": table_name},
            ).scalar()
        )
    except Exception:
        return False


def _convert_to_hypertable(bind, table_name: str, time_column: str) -> None:
    inspector = sa.inspect(bind)
    if table_name not in _table_names(inspector) or _has_hypertable(bind, table_name):
        return

    pk_constraint = inspector.get_pk_constraint(table_name) or {}
    if pk_constraint.get("name"):
        op.drop_constraint(pk_constraint["name"], table_name, type_="primary")

    op.execute(
        sa.text(
            f"""
            SELECT create_hypertable(
                '{table_name}',
                '{time_column}',
                if_not_exists => TRUE,
                migrate_data => TRUE
            );
            """
        )
    )

    inspector = sa.inspect(bind)
    indexes = _index_names(inspector, table_name)
    if "uq_wearable_metrics_id_timestamp" not in indexes:
        op.create_index("uq_wearable_metrics_id_timestamp", table_name, ["id", time_column], unique=True)
    if "ix_wearable_metrics_id" not in indexes:
        op.create_index("ix_wearable_metrics_id", table_name, ["id"], unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _add_enum_value("user_vital_type_enum", "GLUCOSE")
    _add_enum_value("user_vital_type_enum", "BLOOD_PRESSURE_SYSTOLIC")
    _add_enum_value("user_vital_type_enum", "BLOOD_PRESSURE_DIASTOLIC")
    _add_enum_value("user_vital_type_enum", "BODY_TEMPERATURE")

    if "wearable_metrics" not in _table_names(inspector):
        op.create_table(
            "wearable_metrics",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("metric_type", sa.String(length=64), nullable=False),
            sa.Column("value", sa.Float(), nullable=False),
            sa.Column("unit", sa.String(length=32), nullable=False),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source", sa.String(length=64), nullable=False, server_default="google_fit"),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    indexes = _index_names(inspector, "wearable_metrics")
    constraints = _unique_constraint_names(inspector, "wearable_metrics")
    if "ix_wearable_metrics_user_id" not in indexes:
        op.create_index("ix_wearable_metrics_user_id", "wearable_metrics", ["user_id"], unique=False)
    if "ix_wearable_metrics_metric_type" not in indexes:
        op.create_index("ix_wearable_metrics_metric_type", "wearable_metrics", ["metric_type"], unique=False)
    if "ix_wearable_metrics_timestamp" not in indexes:
        op.create_index("ix_wearable_metrics_timestamp", "wearable_metrics", ["timestamp"], unique=False)
    if "ix_wearable_metrics_source" not in indexes:
        op.create_index("ix_wearable_metrics_source", "wearable_metrics", ["source"], unique=False)
    if "ix_wearable_metrics_user_metric_timestamp" not in indexes:
        op.create_index(
            "ix_wearable_metrics_user_metric_timestamp",
            "wearable_metrics",
            ["user_id", "metric_type", "timestamp"],
            unique=False,
        )
    if "uq_wearable_metrics_user_metric_timestamp_source" not in constraints:
        op.create_unique_constraint(
            "uq_wearable_metrics_user_metric_timestamp_source",
            "wearable_metrics",
            ["user_id", "metric_type", "timestamp", "source"],
        )

    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
        _convert_to_hypertable(bind, "wearable_metrics", "timestamp")
    except Exception:
        pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "wearable_metrics" in _table_names(inspector):
        op.drop_table("wearable_metrics")
