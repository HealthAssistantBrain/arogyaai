from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from pipelines.feature_pipeline.service import FeaturePipelineService
from pipelines.ml_pipeline.preprocess import FEATURE_NAMES, build_feature_vector


def test_build_feature_vector_matches_trained_model_order():
    snapshot = {
        "bmi": 24.5,
        "hr_mean_7d": 68.0,
        "steps_avg_7d": 7200.0,
        "sleep_efficiency": 81.0,
        "lifestyle_score": 76.5,
        "activity_score": 60.0,
        "glucose": 104.0,
        "cholesterol": 172.0,
    }

    assert FEATURE_NAMES == (
        "bmi",
        "hr_mean_7d",
        "steps_avg_7d",
        "sleep_efficiency",
        "lifestyle_score",
        "activity_score",
    )
    assert build_feature_vector(snapshot) == [24.5, 68.0, 7200.0, 81.0, 76.5, 60.0]
    assert build_feature_vector(snapshot, ("bmi", "glucose", "cholesterol")) == [24.5, 104.0, 172.0]


def test_build_feature_snapshot_uses_latest_lab_results():
    db = MagicMock()
    user = SimpleNamespace(id=uuid4())
    latest_glucose_at = datetime(2026, 4, 30, 8, 0, tzinfo=timezone.utc)
    latest_cholesterol_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
    lab_rows = [
        SimpleNamespace(name="Glucose (Fasting)", value=108.0, timestamp=latest_glucose_at),
        SimpleNamespace(name="LDL Cholesterol", value=142.0, timestamp=latest_cholesterol_at),
    ]

    vitals_query = MagicMock()
    vitals_query.filter.return_value.order_by.return_value.first.return_value = None

    labs_query = MagicMock()
    labs_query.filter.return_value.order_by.return_value.all.return_value = lab_rows

    conditions_query = MagicMock()
    conditions_query.filter.return_value.all.return_value = [
        SimpleNamespace(condition_name="Diabetes", is_deleted=False),
        SimpleNamespace(condition_name="Hypertension", is_deleted=False),
    ]

    history_query = MagicMock()
    history_query.filter.return_value.order_by.return_value.first.return_value = SimpleNamespace(
        chief_complaint="Chest pain for 2 days",
        associated_symptoms=["fatigue", "dizziness"],
        duration="2 days",
        onset="sudden",
        severity=8,
        created_at=latest_glucose_at,
    )

    bp_query = MagicMock()
    bp_query.filter.return_value.order_by.return_value.first.return_value = None

    db.query.side_effect = [history_query, conditions_query, vitals_query, labs_query, bp_query]

    with patch("pipelines.feature_pipeline.service._latest_profile", return_value=SimpleNamespace(height_cm=172.0, weight_kg=74.0, date_of_birth=None, age=34, gender="female", family_history="Stroke, Type 2 Diabetes", allergies="Penicillin", goals="Mediterranean", sleep_hours=6.5, stress_level=4, occupation="Teacher", city="Kolkata", marital_status="married", surgeries="Appendectomy", hospitalizations=True, hospitalization_details="Observation in 2023", current_medications="Metformin", smoking=False, alcohol=True)), patch(
        "pipelines.feature_pipeline.service.SleepService.get_sleep_summary",
        return_value={"data": {}, "last_updated": None},
    ), patch("pipelines.feature_pipeline.service._recent_heart_rates", return_value=[]), patch(
        "pipelines.feature_pipeline.service._recent_steps",
        return_value=[],
    ), patch(
        "pipelines.feature_pipeline.service._recent_sleep_rows",
        return_value=([], [], 0),
    ), patch(
        "pipelines.feature_pipeline.service._latest_user_vital_value",
        return_value=None,
    ), patch(
        "pipelines.feature_pipeline.service.data_availability_7d",
        return_value={"steps": False, "heart_rate": False, "sleep": False},
    ), patch("pipelines.feature_pipeline.service.hr_mean_7d", return_value=0.0), patch(
        "pipelines.feature_pipeline.service.avg_steps_7d",
        return_value=0.0,
    ), patch(
        "pipelines.feature_pipeline.service.sleep_efficiency_7d",
        return_value=0.0,
    ):
        snapshot = FeaturePipelineService.build_feature_snapshot(db, user, persist=False)

    assert snapshot.glucose == 108.0
    assert snapshot.cholesterol == 142.0
    assert snapshot.source_breakdown["lab_points"] == 2
    assert snapshot.latest_observation_at == latest_glucose_at

    payload = snapshot.to_dict()
    assert payload["glucose"] == 108.0
    assert payload["cholesterol"] == 142.0
    assert payload["sex"] == "female"
    assert payload["sleep"] == 6.5
    assert payload["stress"] == 4
    assert payload["disease_flags"] == {"diabetes": True, "hypertension": True}
    assert payload["family_history_flags"] == {"stroke": True, "type_2_diabetes": True}
    assert payload["symptom_flags"]["chest_pain"] is True
    assert payload["symptom_flags"]["fatigue"] is True
    assert payload["severity_score"] == 8
    assert payload["user_profile"]["occupation"] == "Teacher"
    assert payload["medical_history"]["medications"] == "Metformin"
    assert payload["initial_clinical_snapshot"]["duration"] == "2 days"
