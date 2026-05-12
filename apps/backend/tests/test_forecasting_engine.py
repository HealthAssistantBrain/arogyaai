from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import os
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")
os.environ.setdefault("APP_ENCRYPTION_KEY", "3Fj3JV3w4tJ3vZ8dQ7L0He2Tj2xK0xK9yN8kL8mP9Q0=")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb")

from ai.forecasting.core.forecasting_engine import PredictiveForecastingEngine
from ai.scoring.models.baseline_profile import BaselineMetricProfile, BaselineProfile


def _baseline() -> BaselineProfile:
    now = datetime.now(timezone.utc)
    return BaselineProfile(
        user_id="user-1",
        generated_at=now,
        metrics={
            "activity_steps": BaselineMetricProfile("activity_steps", mean_7d=8400.0, mean_30d=8000.0, std_dev=900.0, sample_count=30),
            "sleep_hours": BaselineMetricProfile("sleep_hours", mean_7d=7.3, mean_30d=7.1, std_dev=0.5, sample_count=30),
            "resting_hr": BaselineMetricProfile("resting_hr", mean_7d=57.0, mean_30d=58.0, std_dev=3.0, sample_count=30),
            "cardiovascular_score": BaselineMetricProfile("cardiovascular_score", mean_7d=82.0, mean_30d=80.0, std_dev=4.0, sample_count=30),
            "metabolic_score": BaselineMetricProfile("metabolic_score", mean_7d=79.0, mean_30d=77.0, std_dev=5.0, sample_count=30),
            "recovery_score": BaselineMetricProfile("recovery_score", mean_7d=81.0, mean_30d=79.0, std_dev=4.0, sample_count=30),
            "sleep_score": BaselineMetricProfile("sleep_score", mean_7d=80.0, mean_30d=78.0, std_dev=4.0, sample_count=30),
            "stress_score": BaselineMetricProfile("stress_score", mean_7d=76.0, mean_30d=74.0, std_dev=5.0, sample_count=30),
            "respiratory_score": BaselineMetricProfile("respiratory_score", mean_7d=86.0, mean_30d=84.0, std_dev=3.0, sample_count=30),
        },
    )


def _context() -> dict:
    return {
        "feature_snapshot": {
            "activity_level": 6200,
            "sleep_duration": 6.2,
            "bmi": 25.2,
        },
        "latest_health_payload": {
            "category_scores": {
                "cardiovascular_score": {"score": 69.0},
                "metabolic_score": {"score": 66.0},
                "recovery_score": {"score": 62.0},
                "sleep_score": {"score": 61.0},
                "stress_score": {"score": 59.0},
                "respiratory_score": {"score": 78.0},
            },
            "metadata": {
                "recovery_signals": {
                    "recovery_proxy": 58.0,
                }
            },
            "anomalies": [
                {"type": "hr_spike", "severity": "high"},
            ],
        },
        "baseline_profile": _baseline(),
        "category_histories": {
            "cardiovascular_score": [78.0, 76.0, 74.0, 72.0, 69.0],
            "metabolic_score": [74.0, 72.0, 70.0, 68.0, 66.0],
            "recovery_score": [74.0, 71.0, 69.0, 65.0, 62.0],
            "sleep_score": [72.0, 70.0, 68.0, 64.0, 61.0],
            "stress_score": [69.0, 67.0, 64.0, 61.0, 59.0],
            "respiratory_score": [84.0, 83.0, 81.0, 80.0, 78.0],
        },
        "wearable_signals": {
            "current": {
                "resting_hr": 64.0,
                "heart_rate": 72.0,
                "hrv": 38.0,
                "spo2": 95.0,
                "sleep_hours": 6.2,
                "activity_steps": 6200.0,
                "blood_pressure_systolic": 131.0,
                "blood_pressure_diastolic": 86.0,
                "sleep_efficiency": 72.0,
                "fatigue_proxy": 18.0,
            },
            "histories": {
                "sleep": [7.1, 6.9, 6.8, 6.5, 6.2],
                "spo2": [97.0, 97.0, 96.5, 96.0, 95.0],
                "fatigue_proxy": [10.0, 12.0, 14.0, 16.0, 18.0],
            },
            "source_coverage": {"wearable": True, "sleep": True, "cardio": True, "respiratory": True},
        },
        "lab_signals": {
            "current": {"glucose": 112.0, "cholesterol": 192.0},
            "histories": {"glucose": [96.0, 101.0, 105.0, 109.0, 112.0]},
            "source_coverage": {"labs": True, "glucose": True, "lipids": True},
        },
        "risk_history": [22.0, 28.0, 31.0, 35.0, 39.0],
        "current_anomalies": [{"type": "hr_spike", "severity": "high"}],
        "memory_context": ["Sleep debt has been worsening over the past week."],
        "latest_risk_score": None,
        "latest_health_score": None,
    }


def _db_without_forecast_history() -> MagicMock:
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    db.query.return_value = query
    return db


def test_predictive_forecast_returns_multiwindow_bundle():
    engine = PredictiveForecastingEngine()
    db = _db_without_forecast_history()
    user = SimpleNamespace(id="user-1")

    with patch.object(engine, "_build_context", return_value=_context()), patch.object(
        engine,
        "_latest_dependency_timestamp",
        return_value=datetime.now(timezone.utc) - timedelta(minutes=5),
    ), patch.object(
        engine,
        "_safety_validate",
        side_effect=lambda payload: {"payload": payload, "safety": {"safe": True}},
    ):
        payload = engine.generate(db, user, persist=False)

    assert payload["status"] == "ready"
    assert set(payload["forecast"].keys()) == {"24h", "72h", "7d", "30d"}
    assert payload["forecast"]["7d"]["domains"]
    assert payload["forecast"]["7d"]["predictions"]
    assert payload["forecast"]["7d"]["trajectories"]
    assert payload["forecast"]["7d"]["alerts"]
    assert 0 <= payload["confidence"] <= 1
    assert payload["forecast"]["7d"]["overall_outlook"] in {"stable", "watchful", "deteriorating"}


def test_predictive_forecast_reuses_fresh_cached_payload():
    engine = PredictiveForecastingEngine()
    generated_at = datetime.now(timezone.utc).isoformat()
    cached_payload = {
        "generated_at": generated_at,
        "status": "ready",
        "forecast": {"24h": {"summary": "cached"}},
    }
    context = _context()
    context["latest_health_payload"] = {"forecasting": cached_payload}

    with patch.object(engine, "_build_context", return_value=context), patch.object(
        engine,
        "_latest_dependency_timestamp",
        return_value=datetime.now(timezone.utc) - timedelta(minutes=10),
    ):
        payload = engine.generate(_db_without_forecast_history(), SimpleNamespace(id="user-1"), persist=False)

    assert payload is cached_payload
