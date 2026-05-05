"""enforce blood pressure integrity

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-05-05 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "f6g7h8i9j0k1"
down_revision: Union[str, Sequence[str], None] = "e5f6g7h8i9j0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "user_vitals" in tables:
        op.execute(
            sa.text(
                """
                DELETE FROM user_vitals
                WHERE id IN (
                    SELECT systolic.id
                    FROM user_vitals AS systolic
                    JOIN user_vitals AS diastolic
                      ON diastolic.user_id = systolic.user_id
                     AND diastolic.timestamp = systolic.timestamp
                     AND diastolic.source = systolic.source
                    WHERE lower(systolic.type::text) = 'blood_pressure_systolic'
                      AND lower(diastolic.type::text) = 'blood_pressure_diastolic'
                      AND systolic.value = diastolic.value
                    UNION
                    SELECT diastolic.id
                    FROM user_vitals AS systolic
                    JOIN user_vitals AS diastolic
                      ON diastolic.user_id = systolic.user_id
                     AND diastolic.timestamp = systolic.timestamp
                     AND diastolic.source = systolic.source
                    WHERE lower(systolic.type::text) = 'blood_pressure_systolic'
                      AND lower(diastolic.type::text) = 'blood_pressure_diastolic'
                      AND systolic.value = diastolic.value
                )
                """
            )
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_invalid_user_vitals_bp_pair()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            DECLARE
                sibling_type text;
                sibling_value double precision;
            BEGIN
                IF lower(NEW.type::text) NOT IN ('blood_pressure_systolic', 'blood_pressure_diastolic') THEN
                    RETURN NEW;
                END IF;

                sibling_type := CASE
                    WHEN lower(NEW.type::text) = 'blood_pressure_systolic' THEN 'blood_pressure_diastolic'
                    ELSE 'blood_pressure_systolic'
                END;

                SELECT uv.value
                  INTO sibling_value
                  FROM user_vitals AS uv
                 WHERE uv.user_id = NEW.user_id
                   AND uv.timestamp = NEW.timestamp
                   AND uv.source = NEW.source
                   AND lower(uv.type::text) = sibling_type
                   AND (NEW.id IS NULL OR uv.id <> NEW.id)
                 ORDER BY uv.created_at DESC NULLS LAST
                 LIMIT 1;

                IF sibling_value IS NOT NULL AND sibling_value = NEW.value THEN
                    RAISE EXCEPTION 'invalid blood pressure pair: systolic and diastolic cannot be equal'
                        USING ERRCODE = '23514';
                END IF;

                RETURN NEW;
            END;
            $$;
            """
        )
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_invalid_user_vitals_bp_pair ON user_vitals;")
        op.execute(
            """
            CREATE TRIGGER trg_prevent_invalid_user_vitals_bp_pair
            BEFORE INSERT OR UPDATE ON user_vitals
            FOR EACH ROW
            EXECUTE FUNCTION prevent_invalid_user_vitals_bp_pair();
            """
        )

    if "wearable_metrics" in tables:
        op.execute(
            sa.text(
                """
                DELETE FROM wearable_metrics
                WHERE lower(metric_type) = 'blood_pressure'
                  AND metadata IS NOT NULL
                  AND metadata->>'systolic' ~ '^-?\\d+(\\.\\d+)?$'
                  AND metadata->>'diastolic' ~ '^-?\\d+(\\.\\d+)?$'
                  AND (metadata->>'systolic')::double precision = (metadata->>'diastolic')::double precision
                """
            )
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_invalid_wearable_bp_metric()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            DECLARE
                systolic_text text;
                diastolic_text text;
            BEGIN
                IF lower(coalesce(NEW.metric_type, '')) <> 'blood_pressure' THEN
                    RETURN NEW;
                END IF;

                systolic_text := NEW.metadata->>'systolic';
                diastolic_text := NEW.metadata->>'diastolic';

                IF systolic_text ~ '^-?\\d+(\\.\\d+)?$'
                   AND diastolic_text ~ '^-?\\d+(\\.\\d+)?$'
                   AND systolic_text::double precision = diastolic_text::double precision THEN
                    RAISE EXCEPTION 'invalid blood pressure metric: systolic and diastolic cannot be equal'
                        USING ERRCODE = '23514';
                END IF;

                RETURN NEW;
            END;
            $$;
            """
        )
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_invalid_wearable_bp_metric ON wearable_metrics;")
        op.execute(
            """
            CREATE TRIGGER trg_prevent_invalid_wearable_bp_metric
            BEFORE INSERT OR UPDATE ON wearable_metrics
            FOR EACH ROW
            EXECUTE FUNCTION prevent_invalid_wearable_bp_metric();
            """
        )

    if "vitals_data" in tables:
        op.execute(
            sa.text(
                """
                UPDATE vitals_data
                   SET blood_pressure_sys = NULL,
                       blood_pressure_dia = NULL
                 WHERE blood_pressure_sys IS NOT NULL
                   AND blood_pressure_dia IS NOT NULL
                   AND blood_pressure_sys = blood_pressure_dia
                """
            )
        )
        check_constraints = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("vitals_data")
            if constraint.get("name")
        }
        if "ck_vitals_data_bp_pair_distinct" not in check_constraints:
            op.create_check_constraint(
                "ck_vitals_data_bp_pair_distinct",
                "vitals_data",
                "(blood_pressure_sys IS NULL OR blood_pressure_dia IS NULL OR blood_pressure_sys <> blood_pressure_dia)",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "user_vitals" in tables:
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_invalid_user_vitals_bp_pair ON user_vitals;")
        op.execute("DROP FUNCTION IF EXISTS prevent_invalid_user_vitals_bp_pair();")

    if "wearable_metrics" in tables:
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_invalid_wearable_bp_metric ON wearable_metrics;")
        op.execute("DROP FUNCTION IF EXISTS prevent_invalid_wearable_bp_metric();")

    if "vitals_data" in tables:
        check_constraints = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("vitals_data")
            if constraint.get("name")
        }
        if "ck_vitals_data_bp_pair_distinct" in check_constraints:
            op.drop_constraint("ck_vitals_data_bp_pair_distinct", "vitals_data", type_="check")
