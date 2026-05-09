"""Fix analytics dashboard trigger field access for non-vital tables.

Revision ID: 20260508_0002
Revises: 20260508_0001
Create Date: 2026-05-08 00:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260508_0002"
down_revision: Union[str, Sequence[str], None] = "20260508_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SAFE_NOTIFY_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION notify_dashboard_updates()
RETURNS trigger AS $$
DECLARE
    affected_user uuid;
    affected_type text;
    payload json;
BEGIN
    affected_user := CASE WHEN TG_OP = 'DELETE' THEN OLD.user_id ELSE NEW.user_id END;
    affected_type := CASE
        WHEN TG_TABLE_NAME = 'user_vitals' THEN CASE
            WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD)->>'type'
            ELSE to_jsonb(NEW)->>'type'
        END
        WHEN TG_TABLE_NAME = 'wearable_metrics' THEN CASE
            WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD)->>'metric_type'
            ELSE to_jsonb(NEW)->>'metric_type'
        END
        ELSE NULL
    END;

    payload := json_build_object(
        'user_id', affected_user::text,
        'table_name', TG_TABLE_NAME,
        'operation', TG_OP,
        'metric_type', affected_type
    );

    PERFORM pg_notify('dashboard_updates', payload::text);
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.execute(_SAFE_NOTIFY_FUNCTION_SQL)


def downgrade() -> None:
    # Keep the safe trigger function in place during rollback so the analytics
    # branch remains operational and does not reintroduce the runtime error.
    op.execute(_SAFE_NOTIFY_FUNCTION_SQL)
