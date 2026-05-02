"""add dashboard recommendation triggers

Revision ID: v5w6x7y8z9a0
Revises: u4v5w6x7y8z9
Create Date: 2026-05-01 18:15:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v5w6x7y8z9a0"
down_revision: Union[str, Sequence[str], None] = "u4v5w6x7y8z9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


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
    _ensure_dashboard_trigger_function()
    _ensure_trigger(inspector, "lab_results", "trg_notify_dashboard_updates_lab_results")
    _ensure_trigger(inspector, "clinical_history", "trg_notify_dashboard_updates_clinical_history")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_notify_dashboard_updates_lab_results ON lab_results;")
    op.execute("DROP TRIGGER IF EXISTS trg_notify_dashboard_updates_clinical_history ON clinical_history;")
