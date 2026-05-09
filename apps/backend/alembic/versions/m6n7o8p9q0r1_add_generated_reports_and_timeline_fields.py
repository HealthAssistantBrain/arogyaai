"""add generated reports and timeline workflow fields

Revision ID: m6n7o8p9q0r1
Revises: h9i0j1k2l3m4
Create Date: 2026-05-08 20:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "m6n7o8p9q0r1"
down_revision = "h9i0j1k2l3m4"
branch_labels = None
depends_on = None


def _table_names(inspector):
    return set(inspector.get_table_names())


def _column_names(inspector, table_name):
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "generated_reports" not in _table_names(inspector):
        op.create_table(
            "generated_reports",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=24), server_default="ready", nullable=False),
            sa.Column("generation_type", sa.String(length=48), server_default="longitudinal_summary", nullable=False),
            sa.Column("source_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("report_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("recommendations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("confidence_score", sa.Numeric(precision=4, scale=2), nullable=True),
            sa.Column("timeline_event_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_generated_reports_user_id", "generated_reports", ["user_id"], unique=False)
        op.create_index("ix_generated_reports_timeline_event_id", "generated_reports", ["timeline_event_id"], unique=False)

    if "timeline_events" in _table_names(inspector):
        timeline_columns = _column_names(inspector, "timeline_events")
        if "event_type" not in timeline_columns:
            op.add_column("timeline_events", sa.Column("event_type", sa.String(length=80), nullable=True))
            op.create_index("ix_timeline_events_event_type", "timeline_events", ["event_type"], unique=False)
        if "source_type" not in timeline_columns:
            op.add_column("timeline_events", sa.Column("source_type", sa.String(length=80), nullable=True))
            op.create_index("ix_timeline_events_source_type", "timeline_events", ["source_type"], unique=False)
        if "summary" not in timeline_columns:
            op.add_column("timeline_events", sa.Column("summary", sa.Text(), nullable=True))
        if "severity" not in timeline_columns:
            op.add_column("timeline_events", sa.Column("severity", sa.String(length=32), nullable=True))
        if "confidence" not in timeline_columns:
            op.add_column("timeline_events", sa.Column("confidence", sa.Numeric(precision=4, scale=2), nullable=True))
        if "source_id" not in timeline_columns:
            op.add_column("timeline_events", sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True))
            op.create_index("ix_timeline_events_source_id", "timeline_events", ["source_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "timeline_events" in _table_names(inspector):
        timeline_columns = _column_names(inspector, "timeline_events")
        if "source_id" in timeline_columns:
            op.drop_index("ix_timeline_events_source_id", table_name="timeline_events")
            op.drop_column("timeline_events", "source_id")
        if "confidence" in timeline_columns:
            op.drop_column("timeline_events", "confidence")
        if "severity" in timeline_columns:
            op.drop_column("timeline_events", "severity")
        if "summary" in timeline_columns:
            op.drop_column("timeline_events", "summary")
        if "source_type" in timeline_columns:
            op.drop_index("ix_timeline_events_source_type", table_name="timeline_events")
            op.drop_column("timeline_events", "source_type")
        if "event_type" in timeline_columns:
            op.drop_index("ix_timeline_events_event_type", table_name="timeline_events")
            op.drop_column("timeline_events", "event_type")

    if "generated_reports" in _table_names(inspector):
        op.drop_index("ix_generated_reports_timeline_event_id", table_name="generated_reports")
        op.drop_index("ix_generated_reports_user_id", table_name="generated_reports")
        op.drop_table("generated_reports")
