"""schema standardization vertical slice

Revision ID: k1l2m3n4o5p6
Revises: 562631f5e9fe, j7k8l9m0n1o2
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "k1l2m3n4o5p6"
down_revision: Union[str, Sequence[str], None] = ("562631f5e9fe", "j7k8l9m0n1o2")
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


def _unique_column_sets(inspector: sa.Inspector, table_name: str) -> dict[str, tuple[str, ...]]:
    if table_name not in _table_names(inspector):
        return {}
    return {
        constraint["name"]: tuple(constraint["column_names"] or ())
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def _create_table_comment(table_name: str, comment: str) -> None:
    op.execute(sa.text(f"COMMENT ON TABLE {table_name} IS :comment").bindparams(comment=comment))


def _has_hypertable(bind, table_name: str) -> bool:
    try:
        result = bind.execute(
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
        return result is not None
    except Exception:
        return False


def _drop_conflicting_uniques_for_hypertable(inspector: sa.Inspector, table_name: str, time_column: str) -> None:
    if table_name not in _table_names(inspector):
        return

    pk_constraint = inspector.get_pk_constraint(table_name) or {}
    pk_name = pk_constraint.get("name")
    if pk_name:
        op.drop_constraint(pk_name, table_name, type_="primary")

    for constraint_name, column_names in _unique_column_sets(inspector, table_name).items():
        if time_column not in column_names:
            op.drop_constraint(constraint_name, table_name, type_="unique")

    for index in inspector.get_indexes(table_name):
        if index.get("unique") and time_column not in tuple(index.get("column_names") or ()):
            op.drop_index(index["name"], table_name=table_name)


def _convert_to_hypertable(
    bind,
    table_name: str,
    time_column: str,
    composite_unique_name: str,
    *,
    lock_tables: Sequence[str] = (),
) -> None:
    inspector = sa.inspect(bind)
    if table_name not in _table_names(inspector) or _has_hypertable(bind, table_name):
        return

    _drop_conflicting_uniques_for_hypertable(inspector, table_name, time_column)
    for lock_table in lock_tables:
        if lock_table in _table_names(inspector):
            op.execute(f"LOCK TABLE {lock_table} IN SHARE ROW EXCLUSIVE MODE")

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
    existing_indexes = _index_names(inspector, table_name)
    if composite_unique_name not in existing_indexes:
        op.create_index(composite_unique_name, table_name, ["id", time_column], unique=True)

    id_index = f"ix_{table_name}_id"
    if id_index not in existing_indexes:
        op.create_index(id_index, table_name, ["id"], unique=False)


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


def _recreate_dashboard_triggers(inspector: sa.Inspector) -> None:
    trigger_targets = {
        "user_vitals": "trg_notify_dashboard_updates_user_vitals",
        "wearable_data": "trg_notify_dashboard_updates_wearable_data",
        "risk_scores": "trg_notify_dashboard_updates_risk_scores",
        "health_scores": "trg_notify_dashboard_updates_health_scores",
        "shap_values": "trg_notify_dashboard_updates_shap_values",
    }

    for table_name, trigger_name in trigger_targets.items():
        if table_name not in _table_names(inspector):
            continue
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
    tables = _table_names(inspector)

    if "user_profile" in tables:
        profile_columns = _column_names(inspector, "user_profile")
        required_profile_columns = {
            "age": sa.Column("age", sa.Integer(), nullable=True),
            "gender": sa.Column("gender", sa.String(length=20), nullable=True),
            "height_cm": sa.Column("height_cm", sa.Numeric(5, 2), nullable=True),
            "weight_kg": sa.Column("weight_kg", sa.Numeric(5, 2), nullable=True),
            "blood_group": sa.Column("blood_group", sa.String(length=5), nullable=True),
            "allergies": sa.Column("allergies", sa.Text(), nullable=True),
        }
        for column_name, column in required_profile_columns.items():
            if column_name not in profile_columns:
                op.add_column("user_profile", column)

    if "health_profiles" in tables and "user_profile" in tables:
        bind.execute(
            sa.text(
                """
                INSERT INTO user_profile (
                    id,
                    user_id,
                    date_of_birth,
                    age,
                    gender,
                    height_cm,
                    weight_kg,
                    blood_group,
                    allergies,
                    created_at,
                    updated_at
                )
                SELECT
                    gen_random_uuid(),
                    hp.user_id,
                    hp.date_of_birth,
                    CASE
                        WHEN hp.date_of_birth IS NOT NULL
                            THEN EXTRACT(YEAR FROM age(current_date, hp.date_of_birth))::int
                        ELSE NULL
                    END,
                    hp.gender::text,
                    hp.height_cm,
                    hp.weight_kg,
                    hp.blood_group,
                    CASE
                        WHEN hp.allergies IS NULL THEN NULL
                        ELSE array_to_string(hp.allergies, ', ')
                    END,
                    COALESCE(hp.created_at, now()),
                    COALESCE(hp.updated_at, now())
                FROM health_profiles hp
                LEFT JOIN user_profile up ON up.user_id = hp.user_id
                WHERE up.user_id IS NULL
                """
            )
        )

        bind.execute(
            sa.text(
                """
                UPDATE user_profile AS up
                SET
                    date_of_birth = COALESCE(up.date_of_birth, hp.date_of_birth),
                    age = COALESCE(
                        up.age,
                        CASE
                            WHEN hp.date_of_birth IS NOT NULL
                                THEN EXTRACT(YEAR FROM age(current_date, hp.date_of_birth))::int
                            ELSE NULL
                        END
                    ),
                    gender = COALESCE(up.gender, hp.gender::text),
                    height_cm = COALESCE(up.height_cm, hp.height_cm),
                    weight_kg = COALESCE(up.weight_kg, hp.weight_kg),
                    blood_group = COALESCE(up.blood_group, hp.blood_group),
                    allergies = COALESCE(
                        up.allergies,
                        CASE
                            WHEN hp.allergies IS NULL THEN NULL
                            ELSE array_to_string(hp.allergies, ', ')
                        END
                    )
                FROM health_profiles hp
                WHERE up.user_id = hp.user_id
                """
            )
        )

        inspector = sa.inspect(bind)
        tables = _table_names(inspector)
        if "health_profiles_legacy" not in tables:
            op.rename_table("health_profiles", "health_profiles_legacy")
            _create_table_comment(
                "health_profiles_legacy",
                "DEPRECATED: data merged into user_profile by schema standardization migration.",
            )

    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    if "lab_values" in tables and "lab_results" in tables:
        bind.execute(
            sa.text(
                """
                INSERT INTO lab_results (
                    id,
                    user_id,
                    report_id,
                    name,
                    value,
                    unit,
                    reference_range,
                    category,
                    status,
                    timestamp,
                    created_at,
                    updated_at
                )
                SELECT
                    lv.id,
                    lv.user_id,
                    lv.report_id,
                    lv.biomarker_name,
                    lv.value,
                    lv.unit,
                    lv.reference_range,
                    lv.category,
                    lv.status,
                    COALESCE(lv.extracted_at, lv.created_at, now()),
                    COALESCE(lv.created_at, now()),
                    COALESCE(lv.updated_at, now())
                FROM lab_values lv
                ON CONFLICT (user_id, report_id, name)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    unit = COALESCE(EXCLUDED.unit, lab_results.unit),
                    reference_range = COALESCE(EXCLUDED.reference_range, lab_results.reference_range),
                    category = COALESCE(EXCLUDED.category, lab_results.category),
                    status = COALESCE(EXCLUDED.status, lab_results.status),
                    timestamp = COALESCE(EXCLUDED.timestamp, lab_results.timestamp),
                    updated_at = GREATEST(lab_results.updated_at, EXCLUDED.updated_at)
                """
            )
        )

        inspector = sa.inspect(bind)
        tables = _table_names(inspector)
        if "lab_values_legacy" not in tables:
            op.rename_table("lab_values", "lab_values_legacy")
            _create_table_comment(
                "lab_values_legacy",
                "DEPRECATED: data merged into lab_results by schema standardization migration.",
            )

    with op.get_context().autocommit_block():
        for value in (
            "BLOOD_PRESSURE_SYSTOLIC",
            "BLOOD_PRESSURE_DIASTOLIC",
            "BODY_TEMPERATURE",
            "CALORIES_BURNED",
        ):
            op.execute(sa.text(f"ALTER TYPE user_vital_type_enum ADD VALUE IF NOT EXISTS '{value}'"))
        op.execute(sa.text("ALTER TYPE user_vital_source_enum ADD VALUE IF NOT EXISTS 'GOOGLE_FIT'"))

    if "user_vitals" in tables:
        bind.execute(sa.text("UPDATE user_vitals SET type = 'HEART_RATE' WHERE type::text = 'heart_rate'"))
        bind.execute(sa.text("UPDATE user_vitals SET type = 'STEPS' WHERE type::text = 'steps'"))
        bind.execute(sa.text("UPDATE user_vitals SET type = 'SLEEP' WHERE type::text = 'sleep'"))
        bind.execute(sa.text("UPDATE user_vitals SET type = 'SPO2' WHERE type::text = 'spo2'"))
        bind.execute(sa.text("UPDATE user_vitals SET source = 'GOOGLE_FIT' WHERE source::text = 'google_fit'"))

    if "vitals_data" in tables and "user_vitals" in tables:
        for sql in (
            """
            INSERT INTO user_vitals (id, user_id, type, value, unit, timestamp, source, created_at)
            SELECT gen_random_uuid(), vd.user_id, 'HEART_RATE', vd.heart_rate_bpm::float, 'bpm', vd.recorded_at, 'GOOGLE_FIT', COALESCE(vd.created_at, now())
            FROM vitals_data vd
            WHERE vd.heart_rate_bpm IS NOT NULL
              AND NOT EXISTS (
                    SELECT 1
                    FROM user_vitals uv
                    WHERE uv.user_id = vd.user_id
                      AND uv.type::text = 'HEART_RATE'
                      AND uv.timestamp = vd.recorded_at
                      AND uv.source::text = 'GOOGLE_FIT'
              )
            """,
            """
            INSERT INTO user_vitals (id, user_id, type, value, unit, timestamp, source, created_at)
            SELECT gen_random_uuid(), vd.user_id, 'SPO2', vd.oxygen_saturation_spo2::float, '%', vd.recorded_at, 'GOOGLE_FIT', COALESCE(vd.created_at, now())
            FROM vitals_data vd
            WHERE vd.oxygen_saturation_spo2 IS NOT NULL
              AND NOT EXISTS (
                    SELECT 1
                    FROM user_vitals uv
                    WHERE uv.user_id = vd.user_id
                      AND uv.type::text = 'SPO2'
                      AND uv.timestamp = vd.recorded_at
                      AND uv.source::text = 'GOOGLE_FIT'
              )
            """,
            """
            INSERT INTO user_vitals (id, user_id, type, value, unit, timestamp, source, created_at)
            SELECT gen_random_uuid(), vd.user_id, 'BLOOD_PRESSURE_SYSTOLIC', vd.blood_pressure_sys::float, 'mmHg', vd.recorded_at, 'GOOGLE_FIT', COALESCE(vd.created_at, now())
            FROM vitals_data vd
            WHERE vd.blood_pressure_sys IS NOT NULL
              AND NOT EXISTS (
                    SELECT 1
                    FROM user_vitals uv
                    WHERE uv.user_id = vd.user_id
                      AND uv.type::text = 'BLOOD_PRESSURE_SYSTOLIC'
                      AND uv.timestamp = vd.recorded_at
                      AND uv.source::text = 'GOOGLE_FIT'
              )
            """,
            """
            INSERT INTO user_vitals (id, user_id, type, value, unit, timestamp, source, created_at)
            SELECT gen_random_uuid(), vd.user_id, 'BLOOD_PRESSURE_DIASTOLIC', vd.blood_pressure_dia::float, 'mmHg', vd.recorded_at, 'GOOGLE_FIT', COALESCE(vd.created_at, now())
            FROM vitals_data vd
            WHERE vd.blood_pressure_dia IS NOT NULL
              AND NOT EXISTS (
                    SELECT 1
                    FROM user_vitals uv
                    WHERE uv.user_id = vd.user_id
                      AND uv.type::text = 'BLOOD_PRESSURE_DIASTOLIC'
                      AND uv.timestamp = vd.recorded_at
                      AND uv.source::text = 'GOOGLE_FIT'
              )
            """,
            """
            INSERT INTO user_vitals (id, user_id, type, value, unit, timestamp, source, created_at)
            SELECT gen_random_uuid(), vd.user_id, 'BODY_TEMPERATURE', vd.body_temperature_c::float, 'celsius', vd.recorded_at, 'GOOGLE_FIT', COALESCE(vd.created_at, now())
            FROM vitals_data vd
            WHERE vd.body_temperature_c IS NOT NULL
              AND NOT EXISTS (
                    SELECT 1
                    FROM user_vitals uv
                    WHERE uv.user_id = vd.user_id
                      AND uv.type::text = 'BODY_TEMPERATURE'
                      AND uv.timestamp = vd.recorded_at
                      AND uv.source::text = 'GOOGLE_FIT'
              )
            """,
        ):
            bind.execute(sa.text(sql))

    if "wearable_data" in tables and "user_vitals" in tables:
        for sql in (
            """
            INSERT INTO user_vitals (id, user_id, type, value, unit, timestamp, source, created_at)
            SELECT gen_random_uuid(), wd.user_id, 'STEPS', wd.step_count::float, 'count', wd.recorded_at, 'GOOGLE_FIT', COALESCE(wd.created_at, now())
            FROM wearable_data wd
            WHERE wd.step_count IS NOT NULL
              AND NOT EXISTS (
                    SELECT 1
                    FROM user_vitals uv
                    WHERE uv.user_id = wd.user_id
                      AND uv.type::text = 'STEPS'
                      AND uv.timestamp = wd.recorded_at
                      AND uv.source::text = 'GOOGLE_FIT'
              )
            """,
            """
            INSERT INTO user_vitals (id, user_id, type, value, unit, timestamp, source, created_at)
            SELECT gen_random_uuid(), wd.user_id, 'SLEEP', ROUND((wd.sleep_duration_minutes::numeric / 60.0), 2)::float, 'hours', wd.recorded_at, 'GOOGLE_FIT', COALESCE(wd.created_at, now())
            FROM wearable_data wd
            WHERE wd.sleep_duration_minutes IS NOT NULL
              AND NOT EXISTS (
                    SELECT 1
                    FROM user_vitals uv
                    WHERE uv.user_id = wd.user_id
                      AND uv.type::text = 'SLEEP'
                      AND uv.timestamp = wd.recorded_at
                      AND uv.source::text = 'GOOGLE_FIT'
              )
            """,
            """
            INSERT INTO user_vitals (id, user_id, type, value, unit, timestamp, source, created_at)
            SELECT gen_random_uuid(), wd.user_id, 'CALORIES_BURNED', wd.calories_burned::float, 'kcal', wd.recorded_at, 'GOOGLE_FIT', COALESCE(wd.created_at, now())
            FROM wearable_data wd
            WHERE wd.calories_burned IS NOT NULL
              AND NOT EXISTS (
                    SELECT 1
                    FROM user_vitals uv
                    WHERE uv.user_id = wd.user_id
                      AND uv.type::text = 'CALORIES_BURNED'
                      AND uv.timestamp = wd.recorded_at
                      AND uv.source::text = 'GOOGLE_FIT'
              )
            """,
        ):
            bind.execute(sa.text(sql))

    if "wearable_data" in tables:
        _create_table_comment(
            "wearable_data",
            "DEPRECATED: canonical wearable time-series data now lives in user_vitals.",
        )

    if "vitals_data" in tables:
        _create_table_comment(
            "vitals_data",
            "DEPRECATED: canonical wearable/vitals time-series data now lives in user_vitals.",
        )

    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    if "risk_scores" in tables:
        risk_columns = _column_names(inspector, "risk_scores")

        if "model_version" not in risk_columns and "ml_model_version" in risk_columns:
            op.alter_column("risk_scores", "ml_model_version", new_column_name="model_version")
        elif "model_version" not in risk_columns:
            op.add_column("risk_scores", sa.Column("model_version", sa.String(length=50), nullable=True))

        inspector = sa.inspect(bind)
        risk_columns = _column_names(inspector, "risk_scores")
        if "run_id" not in risk_columns and "pipeline_run_id" in risk_columns:
            op.alter_column("risk_scores", "pipeline_run_id", new_column_name="run_id")
        elif "run_id" not in risk_columns:
            op.add_column("risk_scores", sa.Column("run_id", sa.String(length=64), nullable=True))

        inspector = sa.inspect(bind)
        risk_columns = _column_names(inspector, "risk_scores")
        if "created_at" not in risk_columns:
            op.add_column(
                "risk_scores",
                sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            )
        if "feature_snapshot_id" not in risk_columns:
            op.add_column(
                "risk_scores",
                sa.Column(
                    "feature_snapshot_id",
                    postgresql.UUID(as_uuid=True),
                    sa.ForeignKey("feature_snapshots.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )

        inspector = sa.inspect(bind)
        for constraint_name, column_names in _unique_column_sets(inspector, "risk_scores").items():
            if column_names == ("report_id",):
                op.drop_constraint(constraint_name, "risk_scores", type_="unique")
        for index in inspector.get_indexes("risk_scores"):
            if index.get("unique") and tuple(index.get("column_names") or ()) == ("report_id",):
                op.drop_index(index["name"], table_name="risk_scores")

        bind.execute(sa.text("UPDATE risk_scores SET created_at = COALESCE(created_at, calculated_at, now())"))
        bind.execute(sa.text("UPDATE risk_scores SET run_id = gen_random_uuid()::text WHERE run_id IS NULL OR run_id = ''"))

        inspector = sa.inspect(bind)
        risk_columns = _column_names(inspector, "risk_scores")
        if "feature_snapshot" in risk_columns and "feature_snapshots" in tables:
            bind.execute(
                sa.text(
                    """
                    CREATE TEMP TABLE tmp_risk_feature_snapshot_map AS
                    SELECT id AS risk_id, gen_random_uuid() AS feature_snapshot_id
                    FROM risk_scores
                    WHERE feature_snapshot_id IS NULL
                      AND feature_snapshot IS NOT NULL
                      AND jsonb_typeof(feature_snapshot) = 'object'
                    """
                )
            )

            bind.execute(
                sa.text(
                    """
                    INSERT INTO feature_snapshots (
                        id,
                        user_id,
                        report_id,
                        hr_mean_7d,
                        steps_avg_7d,
                        sleep_efficiency,
                        bmi,
                        lifestyle_score,
                        activity_score,
                        sleep_score,
                        confidence,
                        latest_observation_at,
                        feature_payload,
                        source_breakdown,
                        created_at,
                        updated_at,
                        calculated_at
                    )
                    SELECT
                        map.feature_snapshot_id,
                        rs.user_id,
                        rs.report_id,
                        NULLIF(rs.feature_snapshot ->> 'hr_mean_7d', '')::numeric,
                        NULLIF(rs.feature_snapshot ->> 'steps_avg_7d', '')::numeric,
                        NULLIF(rs.feature_snapshot ->> 'sleep_efficiency', '')::numeric,
                        NULLIF(rs.feature_snapshot ->> 'bmi', '')::numeric,
                        NULLIF(rs.feature_snapshot ->> 'lifestyle_score', '')::numeric,
                        NULLIF(rs.feature_snapshot ->> 'activity_score', '')::numeric,
                        NULLIF(rs.feature_snapshot ->> 'sleep_score', '')::numeric,
                        NULLIF(rs.feature_snapshot ->> 'confidence', '')::numeric,
                        NULLIF(rs.feature_snapshot ->> 'latest_observation_at', '')::timestamptz,
                        rs.feature_snapshot,
                        CASE
                            WHEN jsonb_typeof(rs.feature_snapshot -> 'source_breakdown') = 'object'
                                THEN rs.feature_snapshot -> 'source_breakdown'
                            ELSE '{}'::jsonb
                        END,
                        COALESCE(rs.created_at, rs.calculated_at, now()),
                        COALESCE(rs.created_at, rs.calculated_at, now()),
                        COALESCE(rs.calculated_at, rs.created_at, now())
                    FROM tmp_risk_feature_snapshot_map map
                    JOIN risk_scores rs ON rs.id = map.risk_id
                    """
                )
            )

            bind.execute(
                sa.text(
                    """
                    UPDATE risk_scores rs
                    SET feature_snapshot_id = map.feature_snapshot_id
                    FROM tmp_risk_feature_snapshot_map map
                    WHERE rs.id = map.risk_id
                      AND rs.feature_snapshot_id IS NULL
                    """
                )
            )
            bind.execute(sa.text("DROP TABLE IF EXISTS tmp_risk_feature_snapshot_map"))
            op.drop_column("risk_scores", "feature_snapshot")

        inspector = sa.inspect(bind)
        risk_indexes = _index_names(inspector, "risk_scores")
        if "ix_risk_scores_feature_snapshot_id" not in risk_indexes:
            op.create_index("ix_risk_scores_feature_snapshot_id", "risk_scores", ["feature_snapshot_id"], unique=False)
        if "ix_risk_scores_run_id" not in risk_indexes:
            op.create_index("ix_risk_scores_run_id", "risk_scores", ["run_id"], unique=False)

    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    if "baseline_metrics" in tables:
        bind.execute(sa.text("CREATE TABLE IF NOT EXISTS baseline_metrics_legacy AS TABLE baseline_metrics WITH NO DATA"))
        bind.execute(
            sa.text(
                """
                WITH ranked AS (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY user_id, metric_name
                            ORDER BY calculated_at DESC NULLS LAST, updated_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
                        ) AS row_number
                    FROM baseline_metrics
                )
                INSERT INTO baseline_metrics_legacy
                SELECT bm.*
                FROM baseline_metrics bm
                JOIN ranked r ON r.id = bm.id
                WHERE r.row_number > 1
                """
            )
        )
        bind.execute(
            sa.text(
                """
                WITH ranked AS (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY user_id, metric_name
                            ORDER BY calculated_at DESC NULLS LAST, updated_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
                        ) AS row_number
                    FROM baseline_metrics
                )
                DELETE FROM baseline_metrics bm
                USING ranked r
                WHERE bm.id = r.id
                  AND r.row_number > 1
                """
            )
        )

        inspector = sa.inspect(bind)
        baseline_uniques = _unique_column_sets(inspector, "baseline_metrics")
        if ("user_id", "metric_name") not in baseline_uniques.values():
            op.create_unique_constraint(
                "uq_baseline_metrics_user_metric",
                "baseline_metrics",
                ["user_id", "metric_name"],
            )

    inspector = sa.inspect(bind)
    tables = _table_names(inspector)
    if "user_vitals" in tables:
        _convert_to_hypertable(
            bind,
            "user_vitals",
            "timestamp",
            "uq_user_vitals_id_timestamp",
            lock_tables=("users",),
        )
    if "wearable_data" in tables:
        _convert_to_hypertable(
            bind,
            "wearable_data",
            "recorded_at",
            "uq_wearable_data_id_recorded_at",
            lock_tables=("users", "devices"),
        )

    inspector = sa.inspect(bind)
    _ensure_dashboard_trigger_function()
    _recreate_dashboard_triggers(inspector)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    for table_name, trigger_name in {
        "user_vitals": "trg_notify_dashboard_updates_user_vitals",
        "wearable_data": "trg_notify_dashboard_updates_wearable_data",
        "risk_scores": "trg_notify_dashboard_updates_risk_scores",
        "health_scores": "trg_notify_dashboard_updates_health_scores",
        "shap_values": "trg_notify_dashboard_updates_shap_values",
    }.items():
        if table_name in tables:
            op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table_name};")
    op.execute("DROP FUNCTION IF EXISTS notify_dashboard_updates();")

    if "baseline_metrics" in tables:
        baseline_uniques = _unique_column_sets(inspector, "baseline_metrics")
        for constraint_name, column_names in baseline_uniques.items():
            if column_names == ("user_id", "metric_name"):
                op.drop_constraint(constraint_name, "baseline_metrics", type_="unique")

    if "risk_scores" in tables:
        risk_columns = _column_names(inspector, "risk_scores")
        if "ml_model_version" not in risk_columns and "model_version" in risk_columns:
            op.alter_column("risk_scores", "model_version", new_column_name="ml_model_version")
        if "pipeline_run_id" not in risk_columns and "run_id" in risk_columns:
            op.alter_column("risk_scores", "run_id", new_column_name="pipeline_run_id")

    inspector = sa.inspect(bind)
    tables = _table_names(inspector)
    if "lab_values_legacy" in tables and "lab_values" not in tables:
        op.rename_table("lab_values_legacy", "lab_values")
    if "health_profiles_legacy" in tables and "health_profiles" not in tables:
        op.rename_table("health_profiles_legacy", "health_profiles")
