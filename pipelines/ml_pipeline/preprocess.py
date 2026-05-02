from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd


MODEL_TYPES: tuple[str, ...] = ("diabetes", "cardio", "sleep")

MODEL_TYPE_ALIASES: dict[str, str] = {
    "diabetes": "diabetes",
    "diabetes_risk": "diabetes",
    "cardio": "cardio",
    "cardiovascular": "cardio",
    "cardiovascular_risk": "cardio",
    "heart": "cardio",
    "sleep": "sleep",
    "sleep_risk": "sleep",
}

TARGET_COLUMNS: dict[str, str] = {
    "diabetes": "diabetes_label",
    "cardio": "cardio_label",
    "sleep": "sleep_label",
}

FEATURE_NAMES: tuple[str, ...] = (
    "age",
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

SAFE_DEFAULTS: dict[str, float] = {
    "age": 45.0,
    "height": 170.0,
    "weight": 70.0,
    "bmi": 24.2,
    "systolic_bp": 120.0,
    "diastolic_bp": 80.0,
    "glucose": 90.0,
    "hba1c": 5.4,
    "cholesterol": 180.0,
    "heart_rate": 72.0,
    "steps": 6000.0,
    "sleep_hours": 7.0,
    "symptom_count": 0.0,
    "symptom_chest_pain": 0.0,
    "symptom_dizziness": 0.0,
    "symptom_fatigue": 0.0,
    "symptom_shortness_of_breath": 0.0,
    "family_history_diabetes": 0.0,
    "family_history_cardiac": 0.0,
    "family_history_hypertension": 0.0,
    "family_history_stroke": 0.0,
}

_FEATURE_ALIASES: dict[str, tuple[str, ...]] = {
    "age": ("age",),
    "bmi": ("bmi",),
    "systolic_bp": ("systolic_bp", "blood_pressure_systolic", "blood_pressure_sys"),
    "diastolic_bp": ("diastolic_bp", "blood_pressure_diastolic", "blood_pressure_dia"),
    "glucose": ("glucose",),
    "hba1c": ("hba1c", "hbA1c", "a1c"),
    "cholesterol": ("cholesterol", "cholesterol_proxy"),
    "heart_rate": ("heart_rate", "hr_mean_7d", "avg_hr", "avg_rhr"),
    "steps": ("steps", "steps_avg_7d", "activity_level"),
    "sleep_hours": ("sleep_hours", "sleep_duration", "sleep"),
    "symptom_count": ("symptom_count", "symptoms_count"),
    "symptom_chest_pain": ("symptom_chest_pain", "chest_pain"),
    "symptom_dizziness": ("symptom_dizziness", "dizziness"),
    "symptom_fatigue": ("symptom_fatigue", "fatigue"),
    "symptom_shortness_of_breath": ("symptom_shortness_of_breath", "shortness_of_breath"),
    "family_history_diabetes": ("family_history_diabetes", "family_diabetes"),
    "family_history_cardiac": ("family_history_cardiac", "family_cardiac", "family_history_heart"),
    "family_history_hypertension": ("family_history_hypertension", "family_hypertension"),
    "family_history_stroke": ("family_history_stroke", "family_stroke"),
}

_NESTED_FLAG_ALIASES: dict[str, tuple[tuple[str, str], ...]] = {
    "symptom_chest_pain": (("symptom_flags", "chest_pain"),),
    "symptom_dizziness": (("symptom_flags", "dizziness"),),
    "symptom_fatigue": (("symptom_flags", "fatigue"),),
    "symptom_shortness_of_breath": (
        ("symptom_flags", "shortness_of_breath"),
        ("symptom_flags", "breathlessness"),
    ),
    "family_history_diabetes": (
        ("family_history_flags", "diabetes"),
        ("family_history_flags", "type_2_diabetes"),
    ),
    "family_history_cardiac": (
        ("family_history_flags", "cardiac"),
        ("family_history_flags", "heart"),
    ),
    "family_history_hypertension": (("family_history_flags", "hypertension"),),
    "family_history_stroke": (("family_history_flags", "stroke"),),
}


def normalize_model_type(value: str | None) -> str:
    if value is None:
        return "diabetes"
    return MODEL_TYPE_ALIASES.get(str(value).strip().lower(), "diabetes")


def _get_snapshot_value(snapshot: Any, field_name: str) -> Any:
    aliases = _FEATURE_ALIASES.get(field_name, (field_name,))

    if isinstance(snapshot, Mapping):
        for alias in aliases:
            if alias in snapshot:
                return snapshot.get(alias)
        for parent_key, child_key in _NESTED_FLAG_ALIASES.get(field_name, ()):
            nested_flags = snapshot.get(parent_key)
            if isinstance(nested_flags, Mapping) and child_key in nested_flags:
                return nested_flags.get(child_key)
        nested_payload = snapshot.get("feature_payload")
        if isinstance(nested_payload, Mapping):
            for alias in aliases:
                if alias in nested_payload:
                    return nested_payload.get(alias)
            for parent_key, child_key in _NESTED_FLAG_ALIASES.get(field_name, ()):
                nested_flags = nested_payload.get(parent_key)
                if isinstance(nested_flags, Mapping) and child_key in nested_flags:
                    return nested_flags.get(child_key)

    for alias in aliases:
        if hasattr(snapshot, alias):
            return getattr(snapshot, alias)

    nested_payload = getattr(snapshot, "feature_payload", None)
    if isinstance(nested_payload, Mapping):
        for alias in aliases:
            if alias in nested_payload:
                return nested_payload.get(alias)
        for parent_key, child_key in _NESTED_FLAG_ALIASES.get(field_name, ()):
            nested_flags = nested_payload.get(parent_key)
            if isinstance(nested_flags, Mapping) and child_key in nested_flags:
                return nested_flags.get(child_key)

    if field_name == "bmi":
        height = _coerce_float(_get_snapshot_value(snapshot, "height"))
        weight = _coerce_float(_get_snapshot_value(snapshot, "weight"))
        if height > 0 and weight > 0:
            return weight / ((height / 100.0) ** 2)

    return None


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        return float(value)
    except (TypeError, ValueError):
        return default


def build_feature_vector(snapshot: Any, feature_names: Sequence[str] | None = None) -> list[float]:
    effective_feature_names = tuple(feature_names or FEATURE_NAMES)
    return [
        _coerce_float(
            _get_snapshot_value(snapshot, field_name),
            default=SAFE_DEFAULTS.get(field_name, 0.0),
        )
        for field_name in effective_feature_names
    ]


def build_feature_map(snapshot: Any, feature_names: Sequence[str] | None = None) -> dict[str, float]:
    effective_feature_names = tuple(feature_names or FEATURE_NAMES)
    vector = build_feature_vector(snapshot, effective_feature_names)
    return dict(zip(effective_feature_names, vector, strict=True))


def _ensure_numeric(working: pd.DataFrame, columns: Sequence[str]) -> None:
    for column in columns:
        if column not in working.columns:
            working[column] = np.nan
        working[column] = pd.to_numeric(working[column], errors="coerce")


def _ensure_boolean(working: pd.DataFrame, columns: Sequence[str]) -> None:
    for column in columns:
        if column not in working.columns:
            working[column] = False
        working[column] = working[column].fillna(False).astype(bool).astype(float)


def _feature_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        raise ValueError("Training dataset is empty; no model was trained.")

    working = dataframe.copy()
    numeric_columns = [
        "age",
        "height",
        "weight",
        "bmi",
        "glucose",
        "hba1c",
        "cholesterol",
        "heart_rate",
        "steps",
        "sleep_hours",
        "systolic_bp",
        "diastolic_bp",
        "symptom_count",
    ]
    boolean_columns = [
        "symptom_chest_pain",
        "symptom_dizziness",
        "symptom_fatigue",
        "symptom_shortness_of_breath",
        "family_history_diabetes",
        "family_history_cardiac",
        "family_history_hypertension",
        "family_history_stroke",
    ]
    _ensure_numeric(working, numeric_columns)
    _ensure_boolean(working, boolean_columns)

    height = working["height"].where(working["height"] > 0, np.nan).fillna(SAFE_DEFAULTS["height"])
    weight = working["weight"].where(working["weight"] > 0, np.nan).fillna(SAFE_DEFAULTS["weight"])
    computed_bmi = weight / ((height / 100.0) ** 2)
    working["bmi"] = working["bmi"].where(working["bmi"].between(10, 60), computed_bmi)
    working["bmi"] = working["bmi"].replace([np.inf, -np.inf], np.nan)

    features = working.loc[:, list(FEATURE_NAMES)].copy()
    features = features.replace([np.inf, -np.inf], np.nan)
    features = features.fillna({name: SAFE_DEFAULTS[name] for name in FEATURE_NAMES})

    return features.astype(float)


def build_target(dataframe: pd.DataFrame, model_type: str = "diabetes") -> pd.Series:
    working = dataframe.copy()
    _ensure_numeric(
        working,
        (
            "bp",
            "glucose",
            "hba1c",
            "systolic_bp",
            "diastolic_bp",
            "cholesterol",
            "heart_rate",
            "sleep_hours",
            "steps",
        ),
    )
    normalized_type = normalize_model_type(model_type)
    label_column = TARGET_COLUMNS[normalized_type]
    if normalized_type == "diabetes":
        rule_target = pd.Series(
            ((working["hba1c"] >= 6.5) | (working["glucose"] >= 126.0)).astype(int),
            index=working.index,
            dtype="Int64",
        )

    elif normalized_type == "cardio":
        bp_signal = working["bp"].fillna(working["systolic_bp"])
        rule_target = pd.Series(
            ((bp_signal >= 140.0) | (working["cholesterol"] >= 240.0)).astype(int),
            index=working.index,
            dtype="Int64",
        )

    else:
        rule_target = pd.Series(
            (working["sleep_hours"] < 5.0).astype(int),
            index=working.index,
            dtype="Int64",
        )

    if label_column not in working.columns:
        return rule_target

    explicit_target = pd.to_numeric(working[label_column], errors="coerce")
    explicit_target = explicit_target.where(explicit_target.isin([0, 1]))
    if explicit_target.notna().any():
        return explicit_target.astype("Int64")
    return rule_target


def preprocess_for_model(dataframe: pd.DataFrame, model_type: str = "diabetes") -> tuple[pd.DataFrame, pd.Series, tuple[str, ...]]:
    features = _feature_frame(dataframe)
    target = build_target(dataframe, model_type=model_type)
    valid_target = target.notna()
    if not bool(valid_target.any()):
        raise ValueError(f"No rows with measured target inputs are available for {normalize_model_type(model_type)} training.")
    return (
        features.loc[valid_target].reset_index(drop=True),
        target.loc[valid_target].astype(int).reset_index(drop=True),
        FEATURE_NAMES,
    )


def preprocess(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, tuple[str, ...]]:
    return preprocess_for_model(dataframe, model_type="diabetes")
