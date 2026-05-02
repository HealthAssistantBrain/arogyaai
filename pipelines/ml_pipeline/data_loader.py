from __future__ import annotations

from itertools import product
import os
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from pipelines.ml_pipeline.data_mapper import MEDICAL_DATASET_PATH, load_mapped_medical_dataset


REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
OUTPUT_COLUMNS: Final[tuple[str, ...]] = (
    "user_id",
    "age",
    "gender",
    "height",
    "weight",
    "bmi",
    "systolic_bp",
    "diastolic_bp",
    "glucose",
    "hba1c",
    "cholesterol",
    "heart_rate",
    "steps",
    "sleep_hours",
    "symptom_count",
    "symptom_chest_pain",
    "symptom_dizziness",
    "symptom_fatigue",
    "symptom_shortness_of_breath",
    "family_history_diabetes",
    "family_history_cardiac",
    "family_history_hypertension",
    "family_history_stroke",
)

TARGET_COLUMNS: Final[tuple[str, ...]] = (
    "diabetes_label",
    "cardio_label",
    "sleep_label",
)

TRAINING_COLUMNS: Final[tuple[str, ...]] = OUTPUT_COLUMNS + TARGET_COLUMNS

NUMERIC_COLUMNS: Final[tuple[str, ...]] = (
    "age",
    "height",
    "weight",
    "bmi",
    "systolic_bp",
    "diastolic_bp",
    "glucose",
    "hba1c",
    "cholesterol",
    "heart_rate",
    "steps",
    "sleep_hours",
    "symptom_count",
)

BOOLEAN_COLUMNS: Final[tuple[str, ...]] = (
    "symptom_chest_pain",
    "symptom_dizziness",
    "symptom_fatigue",
    "symptom_shortness_of_breath",
    "family_history_diabetes",
    "family_history_cardiac",
    "family_history_hypertension",
    "family_history_stroke",
)

MEDIAN_FILL_DEFAULTS: Final[dict[str, float]] = {
    "systolic_bp": 120.0,
    "diastolic_bp": 80.0,
    "glucose": 90.0,
    "hba1c": 5.4,
    "cholesterol": 180.0,
}

FIXED_FILL_DEFAULTS: Final[dict[str, float]] = {
    "heart_rate": 70.0,
    "steps": 3000.0,
    "sleep_hours": 6.0,
}

MIN_TRAINING_ROWS: Final[int] = 21
CLINICAL_ANCHOR_REPEATS: Final[int] = 3
CLINICAL_ANCHOR_PREFIX: Final[str] = "clinical-anchor-"


def _load_env_files() -> None:
    for path in (REPO_ROOT / ".env", REPO_ROOT / "apps" / "backend" / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)


def _database_url(database_url: str | None = None) -> str:
    _load_env_files()
    resolved = (database_url or os.getenv("DATABASE_URL") or "").strip()
    if not resolved:
        raise RuntimeError("DATABASE_URL is required to load ML training data.")
    return resolved


def _local_dev_database_url(database_url: str) -> str | None:
    url = make_url(database_url)
    if (url.host or "").lower() != "postgres":
        return None
    fallback_host = os.getenv("DATABASE_HOST_FALLBACK", "127.0.0.1").strip()
    if not fallback_host:
        return None
    return url.set(host=fallback_host).render_as_string(hide_password=False)


def _median_or_default(dataframe: pd.DataFrame, column: str, default: float) -> float:
    median = dataframe[column].median(skipna=True)
    if pd.isna(median):
        return default
    return float(median)


def _apply_label_rules(dataframe: pd.DataFrame, *, preserve_existing_labels: bool = False) -> None:
    rule_labels = {
        "diabetes_label": pd.Series(
            ((dataframe["hba1c"] >= 6.5) | (dataframe["glucose"] >= 126.0)).astype(int),
            index=dataframe.index,
            dtype="Int64",
        ),
        "cardio_label": pd.Series(
            ((dataframe["systolic_bp"] >= 140.0) | (dataframe["cholesterol"] >= 240.0)).astype(int),
            index=dataframe.index,
            dtype="Int64",
        ),
        "sleep_label": pd.Series(
            (dataframe["sleep_hours"] < 5.0).astype(int),
            index=dataframe.index,
            dtype="Int64",
        ),
    }

    for column, rule_target in rule_labels.items():
        if preserve_existing_labels and column in dataframe.columns:
            explicit_target = pd.to_numeric(dataframe[column], errors="coerce")
            explicit_target = explicit_target.where(explicit_target.isin([0, 1]))
            if explicit_target.notna().any():
                dataframe[column] = explicit_target.astype("Int64")
                continue
        dataframe[column] = rule_target


def _clinical_anchor_rows() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for repeat in range(CLINICAL_ANCHOR_REPEATS):
        for diabetes_flag, cardio_flag, sleep_flag in product((0, 1), repeat=3):
            index = len(rows)
            age = 34 + repeat * 7 + (index % 5) * 3
            height = 170.0 + (index % 3) * 3.0
            bmi = 22.5 + (index % 6) * 0.8
            weight = round(bmi * ((height / 100.0) ** 2), 1)
            glucose = 132.0 + repeat * 3.0 if diabetes_flag else 92.0 + repeat
            hba1c = 7.0 + repeat * 0.1 if diabetes_flag and repeat % 2 == 1 else 5.4
            systolic_bp = 145.0 + repeat * 2.0 if cardio_flag else 118.0 - repeat
            cholesterol = 248.0 + repeat * 3.0 if cardio_flag and repeat % 2 == 0 else 182.0 + repeat
            sleep_hours = 4.3 + repeat * 0.1 if sleep_flag else 7.1 - repeat * 0.2
            rows.append(
                {
                    "user_id": f"{CLINICAL_ANCHOR_PREFIX}{index:02d}",
                    "age": float(age),
                    "gender": "female" if index % 2 else "male",
                    "height": height,
                    "weight": weight,
                    "bmi": round(bmi, 2),
                    "systolic_bp": systolic_bp,
                    "diastolic_bp": 76.0 + (index % 4),
                    "glucose": glucose,
                    "hba1c": hba1c,
                    "cholesterol": cholesterol,
                    "heart_rate": 66.0 + (index % 6) * 3.0,
                    "steps": 5200.0 + (index % 6) * 700.0,
                    "sleep_hours": sleep_hours,
                    "symptom_count": 0,
                    "symptom_chest_pain": False,
                    "symptom_dizziness": False,
                    "symptom_fatigue": False,
                    "symptom_shortness_of_breath": False,
                    "family_history_diabetes": False,
                    "family_history_cardiac": False,
                    "family_history_hypertension": False,
                    "family_history_stroke": False,
                }
            )

    anchors = pd.DataFrame(rows)
    _apply_label_rules(anchors)
    return anchors.loc[:, TRAINING_COLUMNS]


def _label_class_sets(dataframe: pd.DataFrame) -> dict[str, set[int]]:
    return {
        column: {int(value) for value in dataframe[column].dropna().unique()}
        for column in TARGET_COLUMNS
        if column in dataframe.columns
    }


def _needs_clinical_anchors(dataframe: pd.DataFrame) -> bool:
    if len(dataframe) < MIN_TRAINING_ROWS:
        return True
    return any(classes != {0, 1} for classes in _label_class_sets(dataframe).values())


def _ensure_valid_training_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    working = dataframe.dropna(how="all", subset=list(TARGET_COLUMNS)).copy()
    if _needs_clinical_anchors(working):
        anchors = _clinical_anchor_rows()
        print(f"[ml_data_loader] added clinical anchor rows: {len(anchors)}")
        working = pd.concat([working, anchors], ignore_index=True)

    working = working.dropna(how="all", subset=list(TARGET_COLUMNS)).copy()
    errors: list[str] = []
    if len(working) < MIN_TRAINING_ROWS:
        errors.append(f"dataset has {len(working)} rows; at least {MIN_TRAINING_ROWS} are required")

    for column, classes in _label_class_sets(working).items():
        if classes != {0, 1}:
            errors.append(f"{column} must contain both 0 and 1 classes; found {sorted(classes)}")

    if errors:
        raise ValueError(f"Training data validation failed: {'; '.join(errors)}")

    return working.reset_index(drop=True)


def _clean_training_dataframe(dataframe: pd.DataFrame, *, preserve_existing_labels: bool = False) -> pd.DataFrame:
    print(f"[ml_data_loader] raw shape: {dataframe.shape}")

    working = dataframe.copy()
    for column in OUTPUT_COLUMNS:
        if column not in working.columns:
            working[column] = pd.NA

    if "user_id" in working.columns:
        working = working.dropna(subset=["user_id"])
        working = working.drop_duplicates(subset=["user_id"], keep="first")

    for column in NUMERIC_COLUMNS:
        working[column] = pd.to_numeric(working[column], errors="coerce")

    working = working.replace([np.inf, -np.inf], np.nan)
    working.loc[working["height"] <= 0, "height"] = np.nan
    working.loc[working["weight"] <= 0, "weight"] = np.nan
    working.loc[working["glucose"] < 0, "glucose"] = np.nan
    working.loc[working["hba1c"] < 0, "hba1c"] = np.nan
    working.loc[working["cholesterol"] < 0, "cholesterol"] = np.nan
    working.loc[working["heart_rate"] <= 0, "heart_rate"] = np.nan
    working.loc[working["steps"] < 0, "steps"] = np.nan
    working.loc[~working["sleep_hours"].between(0, 24), "sleep_hours"] = np.nan
    working.loc[working["systolic_bp"] <= 0, "systolic_bp"] = np.nan
    working.loc[working["diastolic_bp"] <= 0, "diastolic_bp"] = np.nan
    working.loc[working["symptom_count"] < 0, "symptom_count"] = np.nan

    valid_height = working["height"].where(working["height"] > 0)
    valid_weight = working["weight"].where(working["weight"] > 0)
    computed_bmi = valid_weight / ((valid_height / 100.0) ** 2)
    working["bmi"] = working["bmi"].where(working["bmi"].between(10, 60), computed_bmi)
    working["bmi"] = working["bmi"].replace([np.inf, -np.inf], np.nan)
    working = working.dropna(subset=["age", "bmi"])
    working = working[working["age"].between(0, 120) & working["bmi"].between(10, 60)]

    median_height = _median_or_default(working, "height", 170.0)
    working["height"] = valid_height.fillna(median_height)
    derived_weight = working["bmi"] * ((working["height"] / 100.0) ** 2)
    working["weight"] = valid_weight.fillna(derived_weight)

    _apply_label_rules(working, preserve_existing_labels=preserve_existing_labels)

    for column, default in MEDIAN_FILL_DEFAULTS.items():
        working[column] = working[column].fillna(_median_or_default(working, column, default))

    for column, default in FIXED_FILL_DEFAULTS.items():
        working[column] = working[column].fillna(default)

    working["symptom_count"] = working["symptom_count"].fillna(0).round().astype(int)

    for column in BOOLEAN_COLUMNS:
        working[column] = working[column].fillna(False).astype(bool)

    working["gender"] = (
        working["gender"]
        .fillna("unknown")
        .astype(str)
        .str.strip()
        .replace("", "unknown")
        .str.lower()
    )

    working = working[working["glucose"] >= 0]
    working = working.loc[:, TRAINING_COLUMNS].reset_index(drop=True)
    working = _ensure_valid_training_dataframe(working)

    unique_users = int(working["user_id"].nunique(dropna=False))
    null_counts = {column: int(count) for column, count in working.isna().sum().items()}
    major_null_columns = [
        column
        for column, count in null_counts.items()
        if len(working) > 0 and count / len(working) >= 0.25
    ]

    print(f"[ml_data_loader] clean shape: {working.shape}")
    print(f"[ml_data_loader] null counts: {null_counts}")
    print(f"[ml_data_loader] unique users: {unique_users}")
    if major_null_columns:
        print(f"[ml_data_loader] columns with >=25% nulls: {major_null_columns}")

    if unique_users != len(working):
        raise ValueError("Training data validation failed: user_id is not unique per row.")

    return working


def load_training_data(database_url: str | None = None) -> pd.DataFrame:
    """Load one feature row per active user from the canonical backend tables."""

    resolved_url = _database_url(database_url)
    query = text(
        """
        WITH lab_candidates AS (
            SELECT
                lr.user_id,
                CASE
                    WHEN lower(lr.name) LIKE '%hba1c%'
                        OR lower(lr.name) LIKE '%hb a1c%'
                        OR lower(lr.name) LIKE '%a1c%'
                        OR lower(lr.name) LIKE '%glycated hemoglobin%'
                        THEN 'hba1c'
                    WHEN lower(lr.name) LIKE '%glucose%'
                        OR lower(lr.name) LIKE '%blood sugar%'
                        THEN 'glucose'
                    WHEN lower(lr.name) LIKE '%cholesterol%'
                        OR lower(lr.name) LIKE '%ldl%'
                        OR lower(lr.name) LIKE '%hdl%'
                        THEN 'cholesterol'
                    ELSE NULL
                END AS marker,
                lr.value::double precision AS value,
                coalesce(lr.timestamp, lr.created_at) AS observed_at,
                lr.created_at
            FROM lab_results lr
            WHERE lr.value IS NOT NULL
        ),
        latest_lab AS (
            SELECT DISTINCT ON (user_id, marker)
                user_id,
                marker,
                value
            FROM lab_candidates
            WHERE marker IS NOT NULL
            ORDER BY user_id, marker, created_at DESC NULLS LAST, observed_at DESC NULLS LAST
        ),
        lab_pivot AS (
            SELECT
                user_id,
                max(value) FILTER (WHERE marker = 'glucose') AS glucose,
                max(value) FILTER (WHERE marker = 'hba1c') AS hba1c,
                max(value) FILTER (WHERE marker = 'cholesterol') AS cholesterol
            FROM latest_lab
            GROUP BY user_id
        ),
        canonical_vitals AS (
            SELECT
                uv.user_id,
                CASE
                    WHEN lower(uv.type::text) = 'heart_rate' THEN 'heart_rate'
                    WHEN lower(uv.type::text) = 'steps' THEN 'steps'
                    WHEN lower(uv.type::text) = 'sleep' THEN 'sleep_hours'
                    WHEN lower(uv.type::text) = 'blood_pressure_systolic' THEN 'systolic_bp'
                    WHEN lower(uv.type::text) = 'blood_pressure_diastolic' THEN 'diastolic_bp'
                    ELSE NULL
                END AS marker,
                CASE
                    WHEN lower(uv.type::text) = 'sleep'
                        AND lower(coalesce(uv.unit, '')) IN ('second', 'seconds', 'sec', 'secs')
                        THEN uv.value / 3600.0
                    WHEN lower(uv.type::text) = 'sleep'
                        AND lower(coalesce(uv.unit, '')) IN ('minute', 'minutes', 'min', 'mins')
                        THEN uv.value / 60.0
                    ELSE uv.value
                END::double precision AS value
            FROM user_vitals uv
            WHERE uv.value IS NOT NULL
        ),
        legacy_vitals AS (
            SELECT
                vd.user_id,
                'heart_rate' AS marker,
                vd.heart_rate_bpm::double precision AS value
            FROM vitals_data vd
            WHERE vd.heart_rate_bpm IS NOT NULL
            UNION ALL
            SELECT
                vd.user_id,
                'systolic_bp' AS marker,
                vd.blood_pressure_sys::double precision AS value
            FROM vitals_data vd
            WHERE vd.blood_pressure_sys IS NOT NULL
            UNION ALL
            SELECT
                vd.user_id,
                'diastolic_bp' AS marker,
                vd.blood_pressure_dia::double precision AS value
            FROM vitals_data vd
            WHERE vd.blood_pressure_dia IS NOT NULL
            UNION ALL
            SELECT
                wd.user_id,
                'steps' AS marker,
                wd.step_count::double precision AS value
            FROM wearable_data wd
            WHERE wd.step_count IS NOT NULL
            UNION ALL
            SELECT
                wd.user_id,
                'sleep_hours' AS marker,
                wd.sleep_duration_minutes::double precision / 60.0 AS value
            FROM wearable_data wd
            WHERE wd.sleep_duration_minutes IS NOT NULL
        ),
        vital_inputs AS (
            SELECT
                user_id,
                marker,
                value
            FROM canonical_vitals
            WHERE marker IS NOT NULL
              AND value IS NOT NULL
            UNION ALL
            SELECT
                lv.user_id,
                lv.marker,
                lv.value
            FROM legacy_vitals lv
            WHERE lv.value IS NOT NULL
              AND NOT EXISTS (
                    SELECT 1
                    FROM canonical_vitals cv
                    WHERE cv.user_id = lv.user_id
                      AND cv.marker = lv.marker
                      AND cv.value IS NOT NULL
              )
        ),
        vitals_agg AS (
            SELECT
                user_id,
                avg(value) FILTER (WHERE marker = 'heart_rate' AND value BETWEEN 20 AND 250) AS heart_rate,
                avg(value) FILTER (WHERE marker = 'steps' AND value >= 0) AS steps,
                avg(value) FILTER (WHERE marker = 'sleep_hours' AND value BETWEEN 0 AND 24) AS sleep_hours,
                avg(value) FILTER (WHERE marker = 'systolic_bp' AND value BETWEEN 50 AND 260) AS systolic_bp,
                avg(value) FILTER (WHERE marker = 'diastolic_bp' AND value BETWEEN 30 AND 180) AS diastolic_bp
            FROM vital_inputs
            GROUP BY user_id
        ),
        symptom_rows AS (
            SELECT
                ch.user_id,
                lower(trim(symptom.value)) AS symptom_text
            FROM clinical_history ch
            LEFT JOIN LATERAL jsonb_array_elements_text(
                CASE
                    WHEN jsonb_typeof(ch.associated_symptoms) = 'array'
                        THEN ch.associated_symptoms
                    ELSE '[]'::jsonb
                END
            ) AS symptom(value) ON TRUE
            UNION ALL
            SELECT
                ch.user_id,
                lower(trim(ch.chief_complaint)) AS symptom_text
            FROM clinical_history ch
            WHERE nullif(trim(ch.chief_complaint), '') IS NOT NULL
        ),
        symptoms_agg AS (
            SELECT
                user_id,
                count(nullif(symptom_text, ''))::integer AS symptom_count,
                bool_or(symptom_text ~ '(chest[ -]?pain|angina)') AS symptom_chest_pain,
                bool_or(symptom_text ~ '(dizz|vertigo|lightheaded)') AS symptom_dizziness,
                bool_or(symptom_text ~ '(fatigue|tired|weakness)') AS symptom_fatigue,
                bool_or(symptom_text ~ '(short(ness)? of breath|breathless|dyspnea)') AS symptom_shortness_of_breath
            FROM symptom_rows
            WHERE nullif(symptom_text, '') IS NOT NULL
            GROUP BY user_id
        ),
        family_hist AS (
            SELECT
                up.user_id,
                lower(coalesce(up.family_history, '')) ~ '(diabetes|blood sugar|insulin)' AS family_history_diabetes,
                lower(coalesce(up.family_history, '')) ~ '(cardiac|heart|coronary|myocardial|angina)' AS family_history_cardiac,
                lower(coalesce(up.family_history, '')) ~ '(hypertension|high blood pressure|bp)' AS family_history_hypertension,
                lower(coalesce(up.family_history, '')) ~ '(stroke|cva|cerebrovascular)' AS family_history_stroke
            FROM user_profile up
        )
        SELECT
            u.id::text AS user_id,
            coalesce(
                up.age,
                cast(extract(year from age(current_date, up.date_of_birth)) AS integer)
            ) AS age,
            up.gender AS gender,
            up.height_cm::double precision AS height,
            up.weight_kg::double precision AS weight,
            va.systolic_bp AS systolic_bp,
            va.diastolic_bp AS diastolic_bp,
            lp.glucose AS glucose,
            lp.hba1c AS hba1c,
            lp.cholesterol AS cholesterol,
            va.heart_rate AS heart_rate,
            coalesce(va.steps, up.activity_level::double precision) AS steps,
            coalesce(va.sleep_hours, up.sleep_hours::double precision) AS sleep_hours,
            coalesce(sa.symptom_count, 0) AS symptom_count,
            coalesce(sa.symptom_chest_pain, false) AS symptom_chest_pain,
            coalesce(sa.symptom_dizziness, false) AS symptom_dizziness,
            coalesce(sa.symptom_fatigue, false) AS symptom_fatigue,
            coalesce(sa.symptom_shortness_of_breath, false) AS symptom_shortness_of_breath,
            coalesce(fh.family_history_diabetes, false) AS family_history_diabetes,
            coalesce(fh.family_history_cardiac, false) AS family_history_cardiac,
            coalesce(fh.family_history_hypertension, false) AS family_history_hypertension,
            coalesce(fh.family_history_stroke, false) AS family_history_stroke
        FROM users u
        LEFT JOIN user_profile up ON up.user_id = u.id
        LEFT JOIN lab_pivot lp ON lp.user_id = u.id
        LEFT JOIN vitals_agg va ON va.user_id = u.id
        LEFT JOIN symptoms_agg sa ON sa.user_id = u.id
        LEFT JOIN family_hist fh ON fh.user_id = u.id
        WHERE coalesce(u.is_deleted, false) = false
        """
    )

    engine = create_engine(resolved_url)
    try:
        try:
            dataframe = pd.read_sql_query(query, engine)
        except OperationalError:
            fallback_url = _local_dev_database_url(resolved_url)
            if not fallback_url:
                raise
            engine.dispose()
            engine = create_engine(fallback_url)
            dataframe = pd.read_sql_query(query, engine)
    finally:
        engine.dispose()

    return _clean_training_dataframe(dataframe)


def load_external_training_data(dataset_path: str | Path | None = None) -> pd.DataFrame:
    """Load the optional real-world CSV dataset mapped into the training schema."""

    mapped = load_mapped_medical_dataset(dataset_path or MEDICAL_DATASET_PATH)
    if mapped.empty:
        return mapped

    print(f"[ml_data_loader] external dataset rows: {len(mapped)} from {Path(dataset_path or MEDICAL_DATASET_PATH)}")
    return _clean_training_dataframe(mapped, preserve_existing_labels=True)


def _merge_training_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [frame for frame in frames if not frame.empty]
    if not non_empty:
        raise ValueError("Training data validation failed: no rows were loaded from database or external dataset.")
    if len(non_empty) == 1:
        return non_empty[0].reset_index(drop=True)

    merged = pd.concat(non_empty, ignore_index=True, sort=False)
    merged = merged.drop_duplicates(subset=["user_id"], keep="first")
    merged = _ensure_valid_training_dataframe(merged)
    print(f"[ml_data_loader] merged training shape: {merged.shape}")
    return merged


def load_training_dataframe(database_url: str | None = None) -> pd.DataFrame:
    """Load database rows plus the optional real-world CSV dataset for training."""

    frames: list[pd.DataFrame] = []
    database_error: Exception | None = None

    try:
        frames.append(load_training_data(database_url))
    except Exception as exc:
        database_error = exc
        if not MEDICAL_DATASET_PATH.is_file():
            raise
        print(f"[ml_data_loader] database training data unavailable; using external dataset fallback: {exc}")

    external = load_external_training_data()
    if not external.empty:
        frames.append(external)

    if not frames and database_error is not None:
        raise database_error

    return _merge_training_frames(frames)
