"""Add symptom analysis sessions

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-05-08 19:45:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "h9i0j1k2l3m4"
down_revision: Union[str, Sequence[str], None] = "g8h9i0j1k2l3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symptom_analysis_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chief_complaint", sa.Text(), nullable=False),
        sa.Column("duration", sa.Text(), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("associated_symptoms", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("aggravating_factors", sa.Text(), nullable=True),
        sa.Column("relieving_factors", sa.Text(), nullable=True),
        sa.Column("previous_episodes", sa.Text(), nullable=True),
        sa.Column("medications", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("symptoms_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("prompt_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("analysis_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("possible_causes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("urgency_level", sa.String(length=32), nullable=True),
        sa.Column("risk_level", sa.String(length=32), nullable=True),
        sa.Column("risk_indicators", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("red_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("recommendations", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("confidence_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("analysis_status", sa.String(length=24), nullable=False, server_default=sa.text("'processing'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("saved_to_timeline", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("timeline_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        if_not_exists=True,
    )
    op.create_index("ix_symptom_analysis_sessions_user_id", "symptom_analysis_sessions", ["user_id"], if_not_exists=True)
    op.create_index("ix_symptom_analysis_sessions_timeline_event_id", "symptom_analysis_sessions", ["timeline_event_id"], if_not_exists=True)
    op.create_index("ix_symptom_analysis_sessions_created_at", "symptom_analysis_sessions", ["created_at"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_symptom_analysis_sessions_created_at", table_name="symptom_analysis_sessions", if_exists=True)
    op.drop_index("ix_symptom_analysis_sessions_timeline_event_id", table_name="symptom_analysis_sessions", if_exists=True)
    op.drop_index("ix_symptom_analysis_sessions_user_id", table_name="symptom_analysis_sessions", if_exists=True)
    op.drop_table("symptom_analysis_sessions", if_exists=True)
