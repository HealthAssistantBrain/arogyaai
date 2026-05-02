from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from pipelines.ml_pipeline.data_mapper import map_medical_dataset
from pipelines.ml_pipeline.preprocess import preprocess_for_model


def test_mapper_keeps_source_specific_labels_separate():
    raw = pd.DataFrame(
        [
            {
                "source_dataset": "pima_diabetes",
                "pima_age": 50,
                "pima_glucose": 148,
                "pima_blood_pressure": 72,
                "pima_bmi": 33.6,
                "pima_diabetes_pedigree": 0.627,
                "pima_outcome": 1,
            },
            {
                "source_dataset": "cardiovascular_kaggle",
                "cardio_id": 1,
                "cardio_age_days": 18000,
                "cardio_height": 170,
                "cardio_weight": 80,
                "cardio_ap_hi": 140,
                "cardio_ap_lo": 90,
                "cardio_cholesterol_level": 2,
                "cardio_glucose_level": 1,
                "cardio_active": 1,
                "cardio_outcome": 1,
            },
            {
                "source_dataset": "sleep_health",
                "sleep_person_id": 1,
                "sleep_age": 45,
                "sleep_duration": 7.2,
                "sleep_bmi_category": "Normal",
                "sleep_blood_pressure": "120/80",
                "sleep_heart_rate": 70,
                "sleep_daily_steps": 7000,
                "sleep_disorder": "",
            },
            {
                "source_dataset": "sleep_health",
                "sleep_person_id": 2,
                "sleep_age": 52,
                "sleep_duration": 6.1,
                "sleep_bmi_category": "Obese",
                "sleep_blood_pressure": "140/90",
                "sleep_heart_rate": 78,
                "sleep_daily_steps": 4000,
                "sleep_disorder": "Sleep Apnea",
            },
        ]
    )

    mapped = map_medical_dataset(raw)

    assert mapped["diabetes_label"].notna().sum() == 1
    assert mapped["cardio_label"].notna().sum() == 1
    assert mapped["sleep_label"].dropna().tolist() == [0.0, 1.0]

    _, sleep_target, _ = preprocess_for_model(mapped, "sleep")
    assert sleep_target.tolist() == [0, 1]
