"""pipeline alignment for LOINC labs and realtime alerts

Revision ID: x7y8z9a0b1c2
Revises: w6x7y8z9a0b1
Create Date: 2026-05-02 03:15:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "x7y8z9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "w6x7y8z9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if table_name not in _table_names(inspector):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if table_name not in _table_names(inspector):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _ensure_dashboard_trigger_function() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_dashboard_updates()
        RETURNS trigger AS $$
        DECLARE
            affected_user uuid;
            affected_record uuid;
            affected_type text;
            payload json;
        BEGIN
            affected_user := CASE WHEN TG_OP = 'DELETE' THEN OLD.user_id ELSE NEW.user_id END;
            affected_record := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;

            IF TG_TABLE_NAME = 'user_vitals' THEN
                affected_type := CASE
                    WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD)->>'type'
                    ELSE to_jsonb(NEW)->>'type'
                END;
            ELSE
                affected_type := NULL;
            END IF;

            payload := json_build_object(
                'user_id', affected_user::text,
                'record_id', affected_record::text,
                'table_name', TG_TABLE_NAME,
                'operation', TG_OP,
                'vital_type', affected_type
            );

            PERFORM pg_notify('dashboard_updates', payload::text);
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def _ensure_trigger(inspector: sa.Inspector, table_name: str, trigger_name: str) -> None:
    if table_name not in _table_names(inspector):
        return

    op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name};")
    op.execute(
        f"""
        CREATE TRIGGER {trigger_name}
        AFTER INSERT OR UPDATE OR DELETE ON {table_name}
        FOR EACH ROW
        EXECUTE FUNCTION notify_dashboard_updates();
        """
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "lab_results" in _table_names(inspector):
        if "loinc_code" not in _column_names(inspector, "lab_results"):
            op.add_column("lab_results", sa.Column("loinc_code", sa.String(length=20), nullable=True))

        inspector = sa.inspect(bind)
        if "ix_lab_results_loinc_code" not in _index_names(inspector, "lab_results"):
            op.create_index("ix_lab_results_loinc_code", "lab_results", ["loinc_code"], unique=False)

    _ensure_dashboard_trigger_function()
    inspector = sa.inspect(bind)
    _ensure_trigger(inspector, "alerts", "trg_notify_dashboard_updates_alerts")
    _ensure_trigger(inspector, "notifications", "trg_notify_dashboard_updates_notifications")
    _ensure_trigger(inspector, "lab_results", "trg_notify_dashboard_updates_lab_results")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    if "alerts" in tables:
        op.execute("DROP TRIGGER IF EXISTS trg_notify_dashboard_updates_alerts ON alerts;")
    if "notifications" in tables:
        op.execute("DROP TRIGGER IF EXISTS trg_notify_dashboard_updates_notifications ON notifications;")

    if "lab_results" in tables:
        if "ix_lab_results_loinc_code" in _index_names(inspector, "lab_results"):
            op.drop_index("ix_lab_results_loinc_code", table_name="lab_results")
        if "loinc_code" in _column_names(inspector, "lab_results"):
            op.drop_column("lab_results", "loinc_code")
