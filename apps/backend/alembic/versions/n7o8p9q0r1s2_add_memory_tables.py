"""add long-term memory tables

Revision ID: n7o8p9q0r1s2
Revises: m6n7o8p9q0r1
Create Date: 2026-05-10 22:05:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "n7o8p9q0r1s2"
down_revision: Union[str, Sequence[str], None] = "m6n7o8p9q0r1"
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
    return {index["name"] for index in inspector.get_indexes(table_name) if index.get("name")}


def _unique_constraints(inspector: sa.Inspector, table_name: str) -> dict[str, tuple[str, ...]]:
    if table_name not in _table_names(inspector):
        return {}
    return {
        constraint["name"]: tuple(constraint["column_names"] or ())
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def _pk_columns(inspector: sa.Inspector, table_name: str) -> tuple[str, ...]:
    if table_name not in _table_names(inspector):
        return ()
    return tuple((inspector.get_pk_constraint(table_name) or {}).get("constrained_columns") or ())


def _timescale_available(bind) -> bool:
    try:
        return bool(
            bind.execute(
                sa.text("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
            ).scalar()
        )
    except Exception:
        return False


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


def _safe_execute(sql: str, params: dict[str, object] | None = None) -> None:
    bind = op.get_bind()
    nested = bind.begin_nested()
    try:
        bind.execute(sa.text(sql), params or {})
    except Exception:
        nested.rollback()
    else:
        nested.commit()


def _ensure_extension(name: str) -> None:
    _safe_execute(f"CREATE EXTENSION IF NOT EXISTS {name};")


def _ensure_health_memory_table(bind) -> None:
    inspector = sa.inspect(bind)
    if "health_memory" not in _table_names(inspector):
        op.create_table(
            "health_memory",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("metric_name", sa.Text(), nullable=False),
            sa.Column("metric_value", sa.Float(), nullable=True),
            sa.Column("metric_unit", sa.Text(), nullable=True),
            sa.Column("trend_direction", sa.Text(), nullable=False, server_default=sa.text("'stable'")),
            sa.Column("trend_note", sa.Text(), nullable=True),
            sa.Column("disease_context", sa.Text(), nullable=True),
            sa.Column("source", sa.Text(), nullable=False, server_default=sa.text("'wearable'")),
            sa.Column("risk_level", sa.Text(), nullable=False, server_default=sa.text("'low'")),
            sa.Column("importance", sa.Text(), nullable=False, server_default=sa.text("'medium'")),
            sa.Column("decay_score", sa.Float(), nullable=False, server_default=sa.text("1.0")),
            sa.Column("embedding_id", sa.Text(), nullable=True),
            sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", "created_at", name="pk_health_memory"),
        )
        return

    health_columns = _column_names(inspector, "health_memory")
    if "created_at" not in health_columns:
        op.add_column(
            "health_memory",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        )
    _safe_execute("UPDATE health_memory SET created_at = COALESCE(created_at, now()) WHERE created_at IS NULL;")
    _safe_execute("ALTER TABLE health_memory ALTER COLUMN created_at SET DEFAULT now();")
    _safe_execute("ALTER TABLE health_memory ALTER COLUMN created_at SET NOT NULL;")
    _safe_execute("ALTER TABLE health_memory ALTER COLUMN id SET DEFAULT gen_random_uuid();")


def _ensure_health_memory_primary_key(bind) -> None:
    inspector = sa.inspect(bind)
    if "health_memory" not in _table_names(inspector):
        return

    current_pk = _pk_columns(inspector, "health_memory")
    if set(current_pk) == {"id", "created_at"} and len(current_pk) == 2:
        return

    pk_constraint = inspector.get_pk_constraint("health_memory") or {}
    pk_name = pk_constraint.get("name")
    if pk_name:
        op.drop_constraint(pk_name, "health_memory", type_="primary")

    inspector = sa.inspect(bind)
    for constraint_name, column_names in _unique_constraints(inspector, "health_memory").items():
        if "created_at" not in column_names:
            op.drop_constraint(constraint_name, "health_memory", type_="unique")

    for index in inspector.get_indexes("health_memory"):
        if index.get("unique") and "created_at" not in tuple(index.get("column_names") or ()):
            op.drop_index(index["name"], table_name="health_memory")

    inspector = sa.inspect(bind)
    if not _pk_columns(inspector, "health_memory"):
        op.create_primary_key("pk_health_memory", "health_memory", ["id", "created_at"])


def _ensure_health_memory_indexes(bind) -> None:
    inspector = sa.inspect(bind)
    health_indexes = _index_names(inspector, "health_memory")
    if "ix_health_memory_user_id" not in health_indexes:
        op.create_index("ix_health_memory_user_id", "health_memory", ["user_id"], unique=False)
    if "ix_health_memory_metric_name" not in health_indexes:
        op.create_index("ix_health_memory_metric_name", "health_memory", ["metric_name"], unique=False)
    if "ix_health_memory_created_at" not in health_indexes:
        op.create_index("ix_health_memory_created_at", "health_memory", ["created_at"], unique=False)
    if "ix_health_memory_id" not in health_indexes:
        op.create_index("ix_health_memory_id", "health_memory", ["id"], unique=False)
    if "ix_health_memory_user_created_at" not in health_indexes:
        op.create_index("ix_health_memory_user_created_at", "health_memory", ["user_id", "created_at"], unique=False)
    if "ix_health_memory_user_metric_created_at" not in health_indexes:
        op.create_index(
            "ix_health_memory_user_metric_created_at",
            "health_memory",
            ["user_id", "metric_name", "created_at"],
            unique=False,
        )


def _ensure_health_memory_hypertable(bind) -> None:
    if not _timescale_available(bind) or _has_hypertable(bind, "health_memory"):
        return
    _safe_execute(
        """
        SELECT create_hypertable(
            'health_memory',
            'created_at',
            if_not_exists => TRUE,
            migrate_data => TRUE,
            create_default_indexes => FALSE
        );
        """
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _ensure_extension("pgcrypto")
    _ensure_extension("timescaledb")

    if "episodic_memory" not in _table_names(inspector):
        op.create_table(
            "episodic_memory",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", sa.Text(), nullable=True),
            sa.Column("interaction_summary", sa.Text(), nullable=False),
            sa.Column("symptoms_discussed", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("recommendations_given", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("reports_analyzed", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("outcome_noted", sa.Text(), nullable=True),
            sa.Column("follow_up_needed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("importance", sa.Text(), nullable=False, server_default=sa.text("'medium'")),
            sa.Column("decay_score", sa.Float(), nullable=False, server_default=sa.text("1.0")),
            sa.Column("embedding_id", sa.Text(), nullable=True),
            sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("consent_level", sa.Text(), nullable=False, server_default=sa.text("'standard'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("last_accessed", sa.DateTime(timezone=True), nullable=True),
            sa.Column("access_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("is_encrypted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    inspector = sa.inspect(bind)
    episodic_indexes = _index_names(inspector, "episodic_memory")
    if "ix_episodic_memory_user_id" not in episodic_indexes:
        op.create_index("ix_episodic_memory_user_id", "episodic_memory", ["user_id"], unique=False)
    if "ix_episodic_memory_created_at" not in episodic_indexes:
        op.create_index("ix_episodic_memory_created_at", "episodic_memory", ["created_at"], unique=False)

    if "semantic_memory" not in _table_names(inspector):
        op.create_table(
            "semantic_memory",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("preferred_explanation_depth", sa.Text(), nullable=False, server_default=sa.text("'moderate'")),
            sa.Column("preferred_tone", sa.Text(), nullable=False, server_default=sa.text("'warm'")),
            sa.Column("health_literacy_level", sa.Text(), nullable=False, server_default=sa.text("'medium'")),
            sa.Column("recurring_concerns", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("confirmed_conditions", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("known_allergies", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("lifestyle_notes", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("communication_preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("embedding_id", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_semantic_memory_user_id"),
        )
    inspector = sa.inspect(bind)
    semantic_indexes = _index_names(inspector, "semantic_memory")
    if "ix_semantic_memory_user_id" not in semantic_indexes:
        op.create_index("ix_semantic_memory_user_id", "semantic_memory", ["user_id"], unique=False)

    _ensure_health_memory_table(bind)
    _ensure_health_memory_primary_key(bind)
    _ensure_health_memory_indexes(bind)
    _ensure_health_memory_hypertable(bind)

    inspector = sa.inspect(bind)
    if "emotional_memory" not in _table_names(inspector):
        op.create_table(
            "emotional_memory",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("emotional_tone", sa.Text(), nullable=False),
            sa.Column("trigger_topic", sa.Text(), nullable=True),
            sa.Column("intensity", sa.Float(), nullable=False, server_default=sa.text("0.5")),
            sa.Column("adaptation_applied", sa.Text(), nullable=True),
            sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("session_id", sa.Text(), nullable=True),
            sa.Column("embedding_id", sa.Text(), nullable=True),
            sa.Column("decay_score", sa.Float(), nullable=False, server_default=sa.text("1.0")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    inspector = sa.inspect(bind)
    emotional_indexes = _index_names(inspector, "emotional_memory")
    if "ix_emotional_memory_user_id" not in emotional_indexes:
        op.create_index("ix_emotional_memory_user_id", "emotional_memory", ["user_id"], unique=False)
    if "ix_emotional_memory_created_at" not in emotional_indexes:
        op.create_index("ix_emotional_memory_created_at", "emotional_memory", ["created_at"], unique=False)

    if "memory_summaries" not in _table_names(inspector):
        op.create_table(
            "memory_summaries",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("summary_type", sa.Text(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("covers_from", sa.DateTime(timezone=True), nullable=True),
            sa.Column("covers_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("source_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
            sa.Column("embedding_id", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    inspector = sa.inspect(bind)
    summary_indexes = _index_names(inspector, "memory_summaries")
    if "ix_memory_summaries_user_id" not in summary_indexes:
        op.create_index("ix_memory_summaries_user_id", "memory_summaries", ["user_id"], unique=False)
    if "ix_memory_summaries_created_at" not in summary_indexes:
        op.create_index("ix_memory_summaries_created_at", "memory_summaries", ["created_at"], unique=False)

    if "memory_audit_log" not in _table_names(inspector):
        op.create_table(
            "memory_audit_log",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("action", sa.Text(), nullable=False),
            sa.Column("memory_type", sa.Text(), nullable=True),
            sa.Column("memory_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    inspector = sa.inspect(bind)
    audit_indexes = _index_names(inspector, "memory_audit_log")
    if "ix_memory_audit_log_user_id" not in audit_indexes:
        op.create_index("ix_memory_audit_log_user_id", "memory_audit_log", ["user_id"], unique=False)
    if "ix_memory_audit_log_created_at" not in audit_indexes:
        op.create_index("ix_memory_audit_log_created_at", "memory_audit_log", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in (
        "memory_audit_log",
        "memory_summaries",
        "emotional_memory",
        "health_memory",
        "semantic_memory",
        "episodic_memory",
    ):
        if table_name not in _table_names(inspector):
            continue
        for index_name in _index_names(inspector, table_name):
            op.drop_index(index_name, table_name=table_name)
        op.drop_table(table_name)
        inspector = sa.inspect(bind)
