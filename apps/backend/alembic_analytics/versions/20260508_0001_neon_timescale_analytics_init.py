"""Initialize Neon + Timescale analytics schema.

Revision ID: 20260508_0001
Revises:
Create Date: 2026-05-08 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260508_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = ("analytics",)
depends_on: Union[str, Sequence[str], None] = None

USER_VITAL_TYPE_ENUM = postgresql.ENUM(
    "HEART_RATE",
    "STEPS",
    "SLEEP",
    "SPO2",
    "GLUCOSE",
    "BLOOD_PRESSURE_SYSTOLIC",
    "BLOOD_PRESSURE_DIASTOLIC",
    "BODY_TEMPERATURE",
    "CALORIES_BURNED",
    name="user_vital_type_enum",
    create_type=False,
)
USER_VITAL_SOURCE_ENUM = postgresql.ENUM(
    "GOOGLE_FIT",
    name="user_vital_source_enum",
    create_type=False,
)
RISK_LEVEL_ENUM = postgresql.ENUM(
    "LOW",
    "MODERATE",
    "HIGH",
    "CRITICAL",
    "UNKNOWN",
    name="risk_level_enum",
    create_type=False,
)
REC_CATEGORY_ENUM = postgresql.ENUM(
    "DIET",
    "EXERCISE",
    "MEDICATION",
    "LIFESTYLE",
    "CONSULTATION",
    name="rec_category_enum",
    create_type=False,
)
PRIORITY_ENUM = postgresql.ENUM(
    "LOW",
    "MEDIUM",
    "HIGH",
    "URGENT",
    name="priority_enum",
    create_type=False,
)


def _table_names(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _index_names(bind, table_name: str) -> set[str]:
    return {item["name"] for item in sa.inspect(bind).get_indexes(table_name) if item.get("name")}


def _timescale_available(bind) -> bool:
    return bool(
        bind.execute(
            sa.text("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
        ).scalar()
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


def _safe_execute(sql: str) -> None:
    bind = op.get_bind()
    nested = bind.begin_nested()
    try:
        bind.execute(sa.text(sql))
    except Exception:
        nested.rollback()
    else:
        nested.commit()


def _create_hypertable(bind, table_name: str, time_column: str) -> None:
    if not _timescale_available(bind) or _has_hypertable(bind, table_name):
        return
    _safe_execute(
        f"""
        SELECT create_hypertable(
            '{table_name}',
            '{time_column}',
            if_not_exists => TRUE,
            migrate_data => TRUE,
            create_default_indexes => FALSE
        );
        """
    )


def _create_types() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_vital_type_enum') THEN
                CREATE TYPE user_vital_type_enum AS ENUM (
                    'HEART_RATE',
                    'STEPS',
                    'SLEEP',
                    'SPO2',
                    'GLUCOSE',
                    'BLOOD_PRESSURE_SYSTOLIC',
                    'BLOOD_PRESSURE_DIASTOLIC',
                    'BODY_TEMPERATURE',
                    'CALORIES_BURNED'
                );
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_vital_source_enum') THEN
                CREATE TYPE user_vital_source_enum AS ENUM ('GOOGLE_FIT');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'risk_level_enum') THEN
                CREATE TYPE risk_level_enum AS ENUM ('LOW', 'MODERATE', 'HIGH', 'CRITICAL', 'UNKNOWN');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rec_category_enum') THEN
                CREATE TYPE rec_category_enum AS ENUM ('DIET', 'EXERCISE', 'MEDICATION', 'LIFESTYLE', 'CONSULTATION');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'priority_enum') THEN
                CREATE TYPE priority_enum AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'URGENT');
            END IF;
        END $$;
        """
    )


def _create_dashboard_notify_triggers(bind) -> None:
    tracked_tables = (
        "user_vitals",
        "wearable_metrics",
        "risk_scores",
        "health_scores",
        "feature_snapshots",
        "shap_values",
    )
    existing_tables = _table_names(bind)
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
    )
    for table_name in tracked_tables:
        if table_name not in existing_tables:
            continue
        op.execute(
            f"""
            DROP TRIGGER IF EXISTS trg_notify_dashboard_updates_{table_name} ON {table_name};
            CREATE TRIGGER trg_notify_dashboard_updates_{table_name}
            AFTER INSERT OR UPDATE OR DELETE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION notify_dashboard_updates();
            """
        )


def _create_timescale_objects(bind) -> None:
    if not _timescale_available(bind):
        return

    for table_name, time_column in (
        ("user_vitals", "timestamp"),
        ("wearable_metrics", "timestamp"),
        ("feature_snapshots", "calculated_at"),
        ("risk_scores", "calculated_at"),
        ("health_scores", "calculated_at"),
    ):
        _create_hypertable(bind, table_name, time_column)

    _safe_execute(
        """
        ALTER TABLE user_vitals
        SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'user_id,"type"',
            timescaledb.compress_orderby = 'timestamp DESC'
        );
        """
    )
    _safe_execute(
        """
        ALTER TABLE wearable_metrics
        SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'user_id,metric_type',
            timescaledb.compress_orderby = 'timestamp DESC'
        );
        """
    )
    _safe_execute(
        """
        ALTER TABLE risk_scores
        SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'user_id,risk_level',
            timescaledb.compress_orderby = 'calculated_at DESC'
        );
        """
    )
    _safe_execute(
        """
        ALTER TABLE health_scores
        SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'user_id',
            timescaledb.compress_orderby = 'calculated_at DESC'
        );
        """
    )
    _safe_execute("SELECT add_compression_policy('user_vitals', INTERVAL '30 days');")
    _safe_execute("SELECT add_compression_policy('wearable_metrics', INTERVAL '30 days');")
    _safe_execute("SELECT add_compression_policy('risk_scores', INTERVAL '45 days');")
    _safe_execute("SELECT add_compression_policy('health_scores', INTERVAL '45 days');")
    _safe_execute("SELECT add_retention_policy('user_vitals', INTERVAL '365 days');")
    _safe_execute("SELECT add_retention_policy('wearable_metrics', INTERVAL '365 days');")
    _safe_execute("SELECT add_retention_policy('risk_scores', INTERVAL '730 days');")
    _safe_execute("SELECT add_retention_policy('health_scores', INTERVAL '730 days');")
    _safe_execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS user_vitals_daily_summary
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket(INTERVAL '1 day', timestamp) AS bucket_start,
            user_id,
            "type",
            AVG(value) AS avg_value,
            MIN(value) AS min_value,
            MAX(value) AS max_value,
            COUNT(*) AS sample_count
        FROM user_vitals
        GROUP BY bucket_start, user_id, "type"
        WITH NO DATA;
        """
    )
    _safe_execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS wearable_metrics_daily_summary
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket(INTERVAL '1 day', timestamp) AS bucket_start,
            user_id,
            metric_type,
            AVG(value) AS avg_value,
            MIN(value) AS min_value,
            MAX(value) AS max_value,
            COUNT(*) AS sample_count
        FROM wearable_metrics
        GROUP BY bucket_start, user_id, metric_type
        WITH NO DATA;
        """
    )
    _safe_execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS health_scores_daily_summary
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket(INTERVAL '1 day', calculated_at) AS bucket_start,
            user_id,
            AVG(score) AS avg_score,
            MIN(score) AS min_score,
            MAX(score) AS max_score,
            COUNT(*) AS sample_count
        FROM health_scores
        GROUP BY bucket_start, user_id
        WITH NO DATA;
        """
    )
    _safe_execute(
        """
        SELECT add_continuous_aggregate_policy(
            'user_vitals_daily_summary',
            start_offset => INTERVAL '90 days',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '30 minutes'
        );
        """
    )
    _safe_execute(
        """
        SELECT add_continuous_aggregate_policy(
            'wearable_metrics_daily_summary',
            start_offset => INTERVAL '90 days',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '30 minutes'
        );
        """
    )
    _safe_execute(
        """
        SELECT add_continuous_aggregate_policy(
            'health_scores_daily_summary',
            start_offset => INTERVAL '180 days',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour'
        );
        """
    )


def upgrade() -> None:
    bind = op.get_bind()

    _safe_execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    _safe_execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
    _create_types()

    existing_tables = _table_names(bind)
    if "user_vitals" not in existing_tables:
        op.create_table(
            "user_vitals",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("type", USER_VITAL_TYPE_ENUM, nullable=False),
            sa.Column("value", sa.Float(), nullable=False),
            sa.Column("unit", sa.String(length=20), nullable=False),
            sa.Column("raw_value", sa.Float(), nullable=True),
            sa.Column("raw_unit", sa.String(length=20), nullable=True),
            sa.Column("normalized_value", sa.Float(), nullable=True),
            sa.Column("normalized_unit", sa.String(length=20), nullable=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source", USER_VITAL_SOURCE_ENUM, nullable=False),
            sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("user_id", "type", "timestamp", "source", name="uq_user_vitals_user_type_timestamp_source"),
        )

    if "wearable_metrics" not in existing_tables:
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
            sa.UniqueConstraint(
                "user_id",
                "metric_type",
                "timestamp",
                "source",
                name="uq_wearable_metrics_user_metric_timestamp_source",
            ),
        )

    if "feature_snapshots" not in existing_tables:
        op.create_table(
            "feature_snapshots",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("hr_mean_7d", sa.Numeric(6, 2), nullable=True),
            sa.Column("steps_avg_7d", sa.Numeric(10, 2), nullable=True),
            sa.Column("sleep_efficiency", sa.Numeric(5, 2), nullable=True),
            sa.Column("bmi", sa.Numeric(5, 2), nullable=True),
            sa.Column("lifestyle_score", sa.Numeric(5, 2), nullable=True),
            sa.Column("activity_score", sa.Numeric(5, 2), nullable=True),
            sa.Column("sleep_score", sa.Numeric(5, 2), nullable=True),
            sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
            sa.Column("latest_observation_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("feature_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("source_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )

    if "risk_scores" not in existing_tables:
        op.create_table(
            "risk_scores",
            sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("feature_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("risk_level", RISK_LEVEL_ENUM, nullable=False),
            sa.Column("overall_score", sa.Numeric(5, 2), nullable=False),
            sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
            sa.Column("model_version", sa.String(length=50), nullable=True),
            sa.Column("prediction_source", sa.String(length=40), nullable=True, server_default="rule_engine"),
            sa.Column("prediction_status", sa.String(length=20), nullable=True, server_default="ready"),
            sa.Column("risk_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("health_score", sa.Numeric(5, 2), nullable=True),
            sa.Column("run_id", sa.String(length=64), nullable=True),
            sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )

    if "health_scores" not in existing_tables:
        op.create_table(
            "health_scores",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("risk_score_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("score", sa.Numeric(5, 2), nullable=False),
            sa.Column("risk_component", sa.Numeric(5, 2), nullable=True),
            sa.Column("lifestyle_component", sa.Numeric(5, 2), nullable=True),
            sa.Column("vitals_component", sa.Numeric(5, 2), nullable=True),
            sa.Column("sleep_component", sa.Numeric(5, 2), nullable=True),
            sa.Column("health_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("source", sa.String(length=40), nullable=True),
            sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )

    if "baseline_metrics" not in existing_tables:
        op.create_table(
            "baseline_metrics",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("metric_name", sa.String(length=80), nullable=False),
            sa.Column("mean_7d", sa.Numeric(10, 2), nullable=True),
            sa.Column("mean_30d", sa.Numeric(10, 2), nullable=True),
            sa.Column("std_dev", sa.Numeric(10, 2), nullable=True),
            sa.Column("sample_count", sa.Integer(), nullable=True),
            sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metric_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "metric_name", name="uq_baseline_metrics_user_metric"),
        )

    if "recommendations" not in existing_tables:
        op.create_table(
            "recommendations",
            sa.Column("risk_score_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("category", REC_CATEGORY_ENUM, nullable=False),
            sa.Column("priority", PRIORITY_ENUM, nullable=True),
            sa.Column("recommendation_text", sa.Text(), nullable=False),
            sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if "shap_values" not in existing_tables:
        op.create_table(
            "shap_values",
            sa.Column("prediction_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("feature_name", sa.String(length=120), nullable=False),
            sa.Column("shap_value", sa.Numeric(10, 4), nullable=False),
            sa.Column("abs_shap_value", sa.Numeric(10, 4), nullable=False),
            sa.Column("direction", sa.String(length=20), nullable=False),
            sa.Column("explanation", sa.String(length=500), nullable=True),
            sa.Column("source_type", sa.String(length=30), nullable=True),
            sa.Column("shap_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("prediction_id", "feature_name", name="uq_shap_values_prediction_feature"),
        )

    bind = op.get_bind()
    for table_name, indexes in {
        "user_vitals": (
            ("ix_user_vitals_user_id", ["user_id"], False),
            ("ix_user_vitals_type", ["type"], False),
            ("ix_user_vitals_timestamp", ["timestamp"], False),
            ("ix_user_vitals_user_id_type_timestamp", ["user_id", "type", "timestamp"], False),
            ("uq_user_vitals_id_timestamp", ["id", "timestamp"], True),
        ),
        "wearable_metrics": (
            ("ix_wearable_metrics_user_id", ["user_id"], False),
            ("ix_wearable_metrics_metric_type", ["metric_type"], False),
            ("ix_wearable_metrics_timestamp", ["timestamp"], False),
            ("ix_wearable_metrics_source", ["source"], False),
            ("ix_wearable_metrics_user_metric_timestamp", ["user_id", "metric_type", "timestamp"], False),
            ("uq_wearable_metrics_id_timestamp", ["id", "timestamp"], True),
        ),
        "feature_snapshots": (
            ("ix_feature_snapshots_user_id", ["user_id"], False),
            ("ix_feature_snapshots_calculated_at", ["calculated_at"], False),
            ("uq_feature_snapshots_id_calculated_at", ["id", "calculated_at"], True),
        ),
        "risk_scores": (
            ("ix_risk_scores_user_id", ["user_id"], False),
            ("ix_risk_scores_risk_level", ["risk_level"], False),
            ("ix_risk_scores_calculated_at", ["calculated_at"], False),
            ("ix_risk_scores_user_risk_calculated_at", ["user_id", "risk_level", "calculated_at"], False),
            ("ix_risk_scores_run_id", ["run_id"], False),
            ("uq_risk_scores_id_calculated_at", ["id", "calculated_at"], True),
        ),
        "health_scores": (
            ("ix_health_scores_user_id", ["user_id"], False),
            ("ix_health_scores_calculated_at", ["calculated_at"], False),
            ("ix_health_scores_user_calculated_at", ["user_id", "calculated_at"], False),
            ("uq_health_scores_id_calculated_at", ["id", "calculated_at"], True),
        ),
        "baseline_metrics": (
            ("ix_baseline_metrics_user_id", ["user_id"], False),
            ("ix_baseline_metrics_metric_name", ["metric_name"], False),
            ("ix_baseline_metrics_calculated_at", ["calculated_at"], False),
        ),
        "recommendations": (
            ("ix_recommendations_risk_score_id", ["risk_score_id"], False),
        ),
        "shap_values": (
            ("ix_shap_values_prediction_id", ["prediction_id"], False),
            ("ix_shap_values_user_id", ["user_id"], False),
            ("ix_shap_values_feature_name", ["feature_name"], False),
            ("ix_shap_values_calculated_at", ["calculated_at"], False),
        ),
    }.items():
        if table_name not in _table_names(bind):
            continue
        existing_indexes = _index_names(bind, table_name)
        for index_name, columns, unique in indexes:
            if index_name not in existing_indexes:
                op.create_index(index_name, table_name, columns, unique=unique)

    _create_timescale_objects(bind)
    _create_dashboard_notify_triggers(bind)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in (
        "shap_values",
        "recommendations",
        "baseline_metrics",
        "health_scores",
        "risk_scores",
        "feature_snapshots",
        "wearable_metrics_daily_summary",
        "user_vitals_daily_summary",
        "health_scores_daily_summary",
        "wearable_metrics",
        "user_vitals",
    ):
        if table_name in _table_names(bind):
            if table_name.endswith("_summary"):
                _safe_execute(f"DROP MATERIALIZED VIEW IF EXISTS {table_name};")
            else:
                op.drop_table(table_name)
    _safe_execute("DROP FUNCTION IF EXISTS notify_dashboard_updates();")
