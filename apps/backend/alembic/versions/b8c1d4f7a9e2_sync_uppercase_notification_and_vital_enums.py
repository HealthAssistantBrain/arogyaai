"""sync uppercase notification and vital enums

Revision ID: b8c1d4f7a9e2
Revises: 7f1a9d2b3c4e
Create Date: 2026-04-06 20:10:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8c1d4f7a9e2"
down_revision: Union[str, Sequence[str], None] = "7f1a9d2b3c4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add uppercase enum labels expected by the SQLAlchemy Enum(name=...) mapping.
    with op.get_context().autocommit_block():
        for value in ("HEART_RATE", "STEPS", "SLEEP", "SPO2"):
            op.execute(sa.text(f"ALTER TYPE user_vital_type_enum ADD VALUE IF NOT EXISTS '{value}'"))

        for value in ("AI_INSIGHT", "HEALTH_ALERT", "APPOINTMENT", "SYSTEM", "ACTIVITY"):
            op.execute(sa.text(f"ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS '{value}'"))

        for value in ("INFO", "WARNING", "CRITICAL"):
            op.execute(sa.text(f"ALTER TYPE notification_severity_enum ADD VALUE IF NOT EXISTS '{value}'"))

        op.execute(sa.text("ALTER TYPE user_vital_source_enum ADD VALUE IF NOT EXISTS 'GOOGLE_FIT'"))

    # Backfill legacy lowercase rows so existing data remains readable.
    op.execute(sa.text("UPDATE user_vitals SET type = 'HEART_RATE' WHERE type::text = 'heart_rate'"))
    op.execute(sa.text("UPDATE user_vitals SET type = 'STEPS' WHERE type::text = 'steps'"))
    op.execute(sa.text("UPDATE user_vitals SET type = 'SLEEP' WHERE type::text = 'sleep'"))
    op.execute(sa.text("UPDATE user_vitals SET type = 'SPO2' WHERE type::text = 'spo2'"))
    op.execute(sa.text("UPDATE user_vitals SET source = 'GOOGLE_FIT' WHERE source::text = 'google_fit'"))

    op.execute(sa.text("UPDATE notifications SET type = 'AI_INSIGHT' WHERE type::text = 'ai_insight'"))
    op.execute(sa.text("UPDATE notifications SET type = 'HEALTH_ALERT' WHERE type::text = 'health_alert'"))
    op.execute(sa.text("UPDATE notifications SET type = 'APPOINTMENT' WHERE type::text = 'appointment'"))
    op.execute(sa.text("UPDATE notifications SET type = 'SYSTEM' WHERE type::text = 'system'"))
    op.execute(sa.text("UPDATE notifications SET type = 'ACTIVITY' WHERE type::text = 'activity'"))
    op.execute(sa.text("UPDATE notifications SET severity = 'INFO' WHERE severity::text = 'info'"))
    op.execute(sa.text("UPDATE notifications SET severity = 'WARNING' WHERE severity::text = 'warning'"))
    op.execute(sa.text("UPDATE notifications SET severity = 'CRITICAL' WHERE severity::text = 'critical'"))


def downgrade() -> None:
    # Enum values are not dropped to avoid breaking dependent data or code paths.
    pass
