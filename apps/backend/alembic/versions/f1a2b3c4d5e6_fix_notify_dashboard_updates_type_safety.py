"""fix notify_dashboard_updates type safety

Revision ID: f1a2b3c4d5e6
Revises: d1e2f3a4b5c6
Create Date: 2026-04-15 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_dashboard_updates()
        RETURNS trigger AS $$
        DECLARE
            affected_user uuid;
            affected_type text;
            has_type_column boolean;
            payload json;
        BEGIN
            affected_user := CASE WHEN TG_OP = 'DELETE' THEN OLD.user_id ELSE NEW.user_id END;

            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = TG_TABLE_SCHEMA
                  AND table_name = TG_TABLE_NAME
                  AND column_name = 'type'
            )
            INTO has_type_column;

            IF TG_TABLE_NAME = 'user_vitals' AND has_type_column THEN
                affected_type := CASE
                    WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD)->>'type'
                    ELSE to_jsonb(NEW)->>'type'
                END;
            ELSE
                affected_type := NULL;
            END IF;

            payload := json_build_object(
                'user_id', affected_user::text,
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

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_notify_dashboard_updates_user_vitals ON user_vitals;
        CREATE TRIGGER trg_notify_dashboard_updates_user_vitals
        AFTER INSERT OR UPDATE OR DELETE ON user_vitals
        FOR EACH ROW
        EXECUTE FUNCTION notify_dashboard_updates();
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_notify_dashboard_updates_wearable_data ON wearable_data;
        CREATE TRIGGER trg_notify_dashboard_updates_wearable_data
        AFTER INSERT OR UPDATE OR DELETE ON wearable_data
        FOR EACH ROW
        EXECUTE FUNCTION notify_dashboard_updates();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_dashboard_updates()
        RETURNS trigger AS $$
        DECLARE
            affected_user uuid;
            affected_type text;
            payload json;
        BEGIN
            affected_user := CASE WHEN TG_OP = 'DELETE' THEN OLD.user_id ELSE NEW.user_id END;
            affected_type := CASE
                WHEN TG_TABLE_NAME = 'user_vitals' THEN
                    CASE WHEN TG_OP = 'DELETE' THEN OLD."type"::text ELSE NEW."type"::text END
                ELSE NULL
            END;

            payload := json_build_object(
                'user_id', affected_user::text,
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

    op.execute("DROP TRIGGER IF EXISTS trg_notify_dashboard_updates_user_vitals ON user_vitals;")
    op.execute("DROP TRIGGER IF EXISTS trg_notify_dashboard_updates_wearable_data ON wearable_data;")
    op.execute("DROP FUNCTION IF EXISTS notify_dashboard_updates();")
