from __future__ import annotations

from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd


REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
MEDICAL_DATASET_PATH: Final[Path] = REPO_ROOT / "data" / "medical_dataset.csv"

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


def _empty_training_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=list(TRAINING_COLUMNS))


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        dataframe = pd.read_csv(path, sep=None, engine="python")
    except pd.errors.EmptyDataError:
        return pd.DataFrame()

    # Some mirrors publish PIMA without headers. Detect and name that shape.
    if len(dataframe.columns) == 9 and all(str(column).isdigit() for column in dataframe.columns):
        dataframe = pd.read_csv(path, header=None)
        dataframe.columns = [
            "pima_pregnancies",
            "pima_glucose",
            "pima_blood_pressure",
            "pima_skin_thickness",
            "pima_insulin",
            "pima_bmi",
            "pima_diabetes_pedigree",
            "pima_age",
            "pima_outcome",
        ]

    normalized_columns = {
        column: str(column).strip().replace(" ", "_").replace("/", "_").replace("-", "_")
        for column in dataframe.columns
    }
    dataframe = dataframe.rename(columns=normalized_columns)

    rename_map: dict[str, str] = {}
    if {"Pregnancies", "Glucose", "BloodPressure", "BMI", "DiabetesPedigreeFunction", "Age", "Outcome"}.issubset(
        dataframe.columns
    ):
        rename_map.update(
            {
                "Pregnancies": "pima_pregnancies",
                "Glucose": "pima_glucose",
                "BloodPressure": "pima_blood_pressure",
                "SkinThickness": "pima_skin_thickness",
                "Insulin": "pima_insulin",
                "BMI": "pima_bmi",
                "DiabetesPedigreeFunction": "pima_diabetes_pedigree",
                "Age": "pima_age",
                "Outcome": "pima_outcome",
            }
        )

    if {"age", "height", "weight", "ap_hi", "ap_lo", "cholesterol", "gluc", "cardio"}.issubset(dataframe.columns):
        rename_map.update(
            {
                "id": "cardio_id",
                "age": "cardio_age_days",
                "gender": "cardio_gender",
                "height": "cardio_height",
                "weight": "cardio_weight",
                "ap_hi": "cardio_ap_hi",
                "ap_lo": "cardio_ap_lo",
                "cholesterol": "cardio_cholesterol_level",
                "gluc": "cardio_glucose_level",
                "smoke": "cardio_smoke",
                "alco": "cardio_alcohol",
                "active": "cardio_active",
                "cardio": "cardio_outcome",
            }
        )

    if {"Person_ID", "Age", "Sleep_Duration", "Blood_Pressure", "Sleep_Disorder"}.issubset(dataframe.columns):
        rename_map.update(
            {
                "Person_ID": "sleep_person_id",
                "Gender": "sleep_gender",
                "Age": "sleep_age",
                "Occupation": "sleep_occupation",
                "Sleep_Duration": "sleep_duration",
                "Quality_of_Sleep": "sleep_quality",
                "Physical_Activity_Level": "sleep_physical_activity_level",
                "Stress_Level": "sleep_stress_level",
                "BMI_Category": "sleep_bmi_category",
                "Blood_Pressure": "sleep_blood_pressure",
                "Heart_Rate": "sleep_heart_rate",
                "Daily_Steps": "sleep_daily_steps",
                "Sleep_Disorder": "sleep_disorder",
            }
        )

    return dataframe.rename(columns=rename_map)


def _numeric(dataframe: pd.DataFrame, column: str) -> pd.Series:
    if column not in dataframe.columns:
        return pd.Series(np.nan, index=dataframe.index, dtype="float64")
    return pd.to_numeric(dataframe[column], errors="coerce")


def _text(dataframe: pd.DataFrame, column: str) -> pd.Series:
    if column not in dataframe.columns:
        return pd.Series("", index=dataframe.index, dtype="object")
    return dataframe[column].fillna("").astype(str).str.strip()


def _first_numeric(dataframe: pd.DataFrame, *columns: str) -> pd.Series:
    values = pd.Series(np.nan, index=dataframe.index, dtype="float64")
    for column in columns:
        candidate = _numeric(dataframe, column)
        values = values.fillna(candidate)
    return values


def _first_text(dataframe: pd.DataFrame, *columns: str) -> pd.Series:
    values = pd.Series("", index=dataframe.index, dtype="object")
    for column in columns:
        candidate = _text(dataframe, column)
        values = values.mask(values.eq(""), candidate)
    return values.replace("", pd.NA)


def _binary_label(dataframe: pd.DataFrame, column: str) -> pd.Series:
    values = _numeric(dataframe, column)
    return values.where(values.isin([0, 1]))


def _source(dataframe: pd.DataFrame) -> pd.Series:
    if "source_dataset" in dataframe.columns:
        return _text(dataframe, "source_dataset").str.lower().replace("", "medical")

    source = pd.Series("medical", index=dataframe.index, dtype="object")
    if "pima_outcome" in dataframe.columns or "pima_glucose" in dataframe.columns:
        source = pd.Series("pima_diabetes", index=dataframe.index, dtype="object")
    if "cardio_outcome" in dataframe.columns or "cardio_ap_hi" in dataframe.columns:
        source = pd.Series("cardiovascular_kaggle", index=dataframe.index, dtype="object")
    if "sleep_disorder" in dataframe.columns or "sleep_duration" in dataframe.columns:
        source = pd.Series("sleep_health", index=dataframe.index, dtype="object")
    return source


def _prefixed_user_ids(dataframe: pd.DataFrame, source: pd.Series) -> pd.Series:
    pima_id = pd.Series(dataframe.index.astype(str), index=dataframe.index, dtype="object")
    cardio_id = _text(dataframe, "cardio_id").replace("", pd.NA).fillna(pima_id)
    sleep_id = _text(dataframe, "sleep_person_id").replace("", pd.NA).fillna(pima_id)
    generic_id = _first_text(dataframe, "user_id", "id").fillna(pima_id)

    raw_id = generic_id.mask(source.eq("cardiovascular_kaggle"), cardio_id)
    raw_id = raw_id.mask(source.eq("sleep_health"), sleep_id)
    raw_id = raw_id.mask(source.eq("pima_diabetes"), pima_id)
    return source.astype(str) + "-" + raw_id.astype(str)


def _pima_missing_zero(values: pd.Series) -> pd.Series:
    return values.mask(values <= 0)


def _age_years(dataframe: pd.DataFrame) -> pd.Series:
    age = _first_numeric(dataframe, "age", "Age", "pima_age", "sleep_age")
    cardio_age = _numeric(dataframe, "cardio_age_days")
    cardio_years = cardio_age / 365.25
    age = age.fillna(cardio_years.where(cardio_age > 150, cardio_age))
    return age


def _gender(dataframe: pd.DataFrame, source: pd.Series) -> pd.Series:
    gender = _first_text(dataframe, "gender", "Gender", "sleep_gender")
    cardio_gender = _numeric(dataframe, "cardio_gender")
    cardio_text = cardio_gender.map({1.0: "female", 2.0: "male"})
    gender = gender.fillna(cardio_text)
    gender = gender.mask(source.eq("pima_diabetes") & gender.isna(), "female")
    return gender.fillna("unknown").astype(str).str.lower()


def _blood_pressure(dataframe: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    systolic = _first_numeric(dataframe, "systolic_bp", "cardio_ap_hi")
    diastolic = _first_numeric(dataframe, "diastolic_bp", "cardio_ap_lo")

    sleep_bp = _text(dataframe, "sleep_blood_pressure").str.extract(r"(?P<sys>\d+(?:\.\d+)?)/(?P<dia>\d+(?:\.\d+)?)")
    if not sleep_bp.empty:
        systolic = systolic.fillna(pd.to_numeric(sleep_bp["sys"], errors="coerce"))
        diastolic = diastolic.fillna(pd.to_numeric(sleep_bp["dia"], errors="coerce"))

    pima_bp = _pima_missing_zero(_numeric(dataframe, "pima_blood_pressure"))
    diastolic = diastolic.fillna(pima_bp)
    return systolic, diastolic


def _coded_cholesterol(dataframe: pd.DataFrame) -> pd.Series:
    coded = _numeric(dataframe, "cardio_cholesterol_level")
    mapped = coded.map({1.0: 180.0, 2.0: 220.0, 3.0: 260.0})
    return _first_numeric(dataframe, "cholesterol").fillna(mapped)


def _coded_glucose(dataframe: pd.DataFrame) -> pd.Series:
    coded = _numeric(dataframe, "cardio_glucose_level")
    mapped = coded.map({1.0: 95.0, 2.0: 115.0, 3.0: 145.0})
    pima_glucose = _pima_missing_zero(_numeric(dataframe, "pima_glucose"))
    return _first_numeric(dataframe, "glucose").fillna(pima_glucose).fillna(mapped)


def _bmi_from_category(dataframe: pd.DataFrame) -> pd.Series:
    category = _text(dataframe, "sleep_bmi_category").str.lower()
    return pd.Series(
        np.select(
            [
                category.str.contains("under", na=False),
                category.str.contains("normal", na=False),
                category.str.contains("overweight", na=False),
                category.str.contains("obese", na=False),
            ],
            [18.0, 22.0, 27.5, 32.5],
            default=np.nan,
        ),
        index=dataframe.index,
        dtype="float64",
    )


def _bmi(dataframe: pd.DataFrame) -> pd.Series:
    height = _numeric(dataframe, "cardio_height")
    weight = _numeric(dataframe, "cardio_weight")
    computed = weight / ((height / 100.0) ** 2)
    pima_bmi = _pima_missing_zero(_numeric(dataframe, "pima_bmi"))
    return _first_numeric(dataframe, "bmi").fillna(pima_bmi).fillna(computed).fillna(_bmi_from_category(dataframe))


def _steps(dataframe: pd.DataFrame) -> pd.Series:
    steps = _first_numeric(dataframe, "steps", "sleep_daily_steps")
    active = _numeric(dataframe, "cardio_active")
    activity_proxy = active.map({0.0: 3000.0, 1.0: 7000.0})
    return steps.fillna(activity_proxy)


def _family_history_diabetes(dataframe: pd.DataFrame) -> pd.Series:
    explicit = _numeric(dataframe, "family_history_diabetes")
    pedigree = _numeric(dataframe, "pima_diabetes_pedigree")
    if pedigree.notna().any():
        threshold = float(pedigree.median(skipna=True))
        explicit = explicit.fillna((pedigree >= threshold).astype(float))
    return explicit


def _sleep_label(dataframe: pd.DataFrame, source: pd.Series) -> pd.Series:
    explicit = _binary_label(dataframe, "sleep_label")
    disorder = _text(dataframe, "sleep_disorder").str.lower()
    is_sleep_row = source.eq("sleep_health") | _numeric(dataframe, "sleep_duration").notna()
    has_disorder = disorder.ne("") & disorder.ne("none") & disorder.ne("nan")
    inferred = has_disorder.astype(float).where(is_sleep_row | disorder.ne(""), np.nan)
    return explicit.fillna(inferred)


def _symptom_count(dataframe: pd.DataFrame) -> pd.Series:
    symptom_count = _numeric(dataframe, "symptom_count")
    symptom_text = _first_text(dataframe, "symptoms", "symptom_text", "chief_complaint")
    inferred_count = symptom_text.fillna("").str.split(r"[,;|]").map(
        lambda values: len([value for value in values if str(value).strip()])
    )
    return symptom_count.fillna(inferred_count.where(symptom_text.notna(), np.nan))


def map_medical_dataset(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        return _empty_training_frame()

    source = _source(dataframe)
    systolic_bp, diastolic_bp = _blood_pressure(dataframe)

    mapped = pd.DataFrame(index=dataframe.index)
    mapped["user_id"] = _prefixed_user_ids(dataframe, source)
    mapped["age"] = _age_years(dataframe)
    mapped["gender"] = _gender(dataframe, source)
    mapped["height"] = _first_numeric(dataframe, "height", "cardio_height")
    mapped["weight"] = _first_numeric(dataframe, "weight", "cardio_weight")
    mapped["bmi"] = _bmi(dataframe)
    mapped["systolic_bp"] = systolic_bp
    mapped["diastolic_bp"] = diastolic_bp
    mapped["glucose"] = _coded_glucose(dataframe)
    mapped["hba1c"] = _first_numeric(dataframe, "hba1c")
    mapped["cholesterol"] = _coded_cholesterol(dataframe)
    mapped["heart_rate"] = _first_numeric(dataframe, "heart_rate", "sleep_heart_rate")
    mapped["steps"] = _steps(dataframe)
    mapped["sleep_hours"] = _first_numeric(dataframe, "sleep_hours", "sleep_duration")
    mapped["symptom_count"] = _symptom_count(dataframe)
    mapped["symptom_chest_pain"] = _numeric(dataframe, "symptom_chest_pain")
    mapped["symptom_dizziness"] = _numeric(dataframe, "symptom_dizziness")
    mapped["symptom_fatigue"] = _numeric(dataframe, "symptom_fatigue")
    mapped["symptom_shortness_of_breath"] = _numeric(dataframe, "symptom_shortness_of_breath")
    mapped["family_history_diabetes"] = _family_history_diabetes(dataframe)
    mapped["family_history_cardiac"] = _numeric(dataframe, "family_history_cardiac")
    mapped["family_history_hypertension"] = _numeric(dataframe, "family_history_hypertension")
    mapped["family_history_stroke"] = _numeric(dataframe, "family_history_stroke")
    mapped["diabetes_label"] = _binary_label(dataframe, "diabetes_label").fillna(_binary_label(dataframe, "pima_outcome"))
    mapped["cardio_label"] = _binary_label(dataframe, "cardio_label").fillna(_binary_label(dataframe, "cardio_outcome"))
    mapped["sleep_label"] = _sleep_label(dataframe, source)

    return mapped.loc[:, list(TRAINING_COLUMNS)].reset_index(drop=True)


def load_mapped_medical_dataset(path: str | Path | None = None) -> pd.DataFrame:
    dataset_path = Path(path) if path is not None else MEDICAL_DATASET_PATH
    if not dataset_path.is_file():
        return _empty_training_frame()
    return map_medical_dataset(_read_csv(dataset_path))
