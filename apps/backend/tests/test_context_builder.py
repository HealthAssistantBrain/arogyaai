from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from models import UserVitalTypeEnum
from services import context_builder
from services.context_builder import VitalReading


def test_compute_trend_classifies_recent_numeric_values():
    assert context_builder.compute_trend([100, 110, 120, 130, 140]) == "increasing"
    assert context_builder.compute_trend([140, 130, 120, 110, 100]) == "decreasing"
    assert context_builder.compute_trend([100, 101, 99, 100, 101]) == "stable"
    assert context_builder.compute_trend([100, None]) == "unknown"


def test_get_latest_vitals_normalizes_values(monkeypatch):
    rows = [
        SimpleNamespace(vital_type=UserVitalTypeEnum.STEPS, value=4123.4, unit="count", timestamp=5),
        SimpleNamespace(vital_type=UserVitalTypeEnum.HEART_RATE, value=87.2, unit="bpm", timestamp=5),
        SimpleNamespace(vital_type=UserVitalTypeEnum.SLEEP, value=390, unit="minutes", timestamp=5),
        SimpleNamespace(vital_type=UserVitalTypeEnum.SPO2, value=97.44, unit="%", timestamp=5),
        SimpleNamespace(vital_type=UserVitalTypeEnum.GLUCOSE, value=6.1, unit="mmol/L", timestamp=5),
        SimpleNamespace(vital_type=UserVitalTypeEnum.BODY_TEMPERATURE, value=98.6, unit="F", timestamp=5),
        SimpleNamespace(vital_type=UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC, value=128, unit="mmHg", timestamp=5),
        SimpleNamespace(vital_type=UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC, value=82, unit="mmHg", timestamp=5),
    ]

    monkeypatch.setattr(context_builder, "_fetch_vital_rows", lambda db, user_id: rows)
    monkeypatch.setattr(context_builder, "_latest_from_wearables", lambda db, user_id, metric: VitalReading(metric, None))

    vitals = context_builder.get_latest_vitals("user-1", db=object())

    assert vitals == {
        "steps": 4123,
        "heart_rate": 87,
        "sleep": 6.5,
        "spo2": 97.4,
        "glucose": 109.9,
        "blood_pressure": "128/82",
        "temperature": 37.0,
    }


def test_get_latest_vitals_blocks_duplicate_blood_pressure(monkeypatch):
    rows = [
        SimpleNamespace(vital_type=UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC, value=122, unit="mmHg", timestamp=5),
        SimpleNamespace(vital_type=UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC, value=122, unit="mmHg", timestamp=5),
    ]

    monkeypatch.setattr(context_builder, "_fetch_vital_rows", lambda db, user_id: rows)
    monkeypatch.setattr(context_builder, "_latest_from_wearables", lambda db, user_id, metric: VitalReading(metric, None))

    vitals = context_builder.get_latest_vitals("user-1", db=object())

    assert vitals["blood_pressure"] is None


def test_fetch_predictions_extracts_condition_risks(monkeypatch):
    risk_score = SimpleNamespace(
        risk_payload={"risks": {"diabetes": 0.72, "cardiovascular_risk": 64}},
        confidence_score=0.83,
        overall_score=0.66,
    )

    predictions = context_builder._prediction_items_from_payload(risk_score)

    assert predictions == [
        {"condition": "diabetes", "risk": 0.72, "confidence": 0.83},
        {"condition": "cardiovascular", "risk": 0.64, "confidence": 0.83},
    ]


def test_build_context_returns_exact_shape_with_missing_data(monkeypatch):
    monkeypatch.setattr(context_builder, "_fetch_vital_rows", lambda db, user_id: [])
    monkeypatch.setattr(context_builder, "_get_profile", lambda db, user_id: None)
    monkeypatch.setattr(context_builder, "fetch_predictions", lambda user_id, db=None: [])
    monkeypatch.setattr(context_builder, "get_latest_vitals", lambda user_id, db=None: context_builder._empty_vitals())
    monkeypatch.setattr(context_builder, "_build_trends", lambda db, user_id, vital_rows: context_builder._empty_trends())
    monkeypatch.setattr(context_builder, "_fetch_symptoms", lambda db, user_id: [])

    payload = context_builder.build_context("user-1", db=object())

    assert list(payload.keys()) == ["user_profile", "risk_predictions", "vitals", "trends", "symptoms"]
    assert payload["user_profile"] == {"age": None, "gender": None, "weight": None, "height": None}
    assert payload["risk_predictions"] == []
    assert payload["vitals"] == context_builder._empty_vitals()
    assert payload["trends"] == context_builder._empty_trends()
    assert payload["symptoms"] == []
