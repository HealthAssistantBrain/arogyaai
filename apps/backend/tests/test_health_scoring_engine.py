from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.scoring.analytics.anomaly_detector import AnomalyDetector
from ai.scoring.analytics.confidence_engine import ConfidenceEngine
from ai.scoring.analytics.trend_engine import TrendEngine
from ai.scoring.core.baseline_engine import BaselineEngine
from ai.scoring.core.scoring_engine import ScoringEngine
from ai.scoring.models.baseline_profile import BaselineMetricProfile, BaselineProfile
from ai.scoring.realtime.event_listener import ScoringEventListener


def _baseline() -> BaselineProfile:
    now = datetime.now(timezone.utc)
    return BaselineProfile(
        user_id="user-1",
        generated_at=now,
        metrics={
            "heart_rate": BaselineMetricProfile("heart_rate", mean_7d=62.0, mean_30d=63.0, std_dev=4.0, sample_count=30),
            "resting_hr": BaselineMetricProfile("resting_hr", mean_7d=58.0, mean_30d=59.0, std_dev=3.0, sample_count=30),
            "hrv": BaselineMetricProfile("hrv", mean_7d=55.0, mean_30d=53.0, std_dev=6.0, sample_count=30),
            "sleep_hours": BaselineMetricProfile("sleep_hours", mean_7d=7.4, mean_30d=7.2, std_dev=0.6, sample_count=30),
            "spo2": BaselineMetricProfile("spo2", mean_7d=97.8, mean_30d=97.6, std_dev=0.7, sample_count=30),
            "blood_pressure_systolic": BaselineMetricProfile("blood_pressure_systolic", mean_7d=118.0, mean_30d=119.0, std_dev=5.0, sample_count=30),
            "blood_pressure_diastolic": BaselineMetricProfile("blood_pressure_diastolic", mean_7d=76.0, mean_30d=77.0, std_dev=4.0, sample_count=30),
            "activity_steps": BaselineMetricProfile("activity_steps", mean_7d=8200.0, mean_30d=7800.0, std_dev=1200.0, sample_count=30),
            "health_score": BaselineMetricProfile("health_score", mean_7d=79.0, mean_30d=77.0, std_dev=4.0, sample_count=30),
        },
    )


def _wearable_signals(now: datetime | None = None) -> dict[str, object]:
    current_time = now or datetime.now(timezone.utc)
    return {
        "current": {
            "heart_rate": 64.0,
            "resting_hr": 57.0,
            "hrv": 58.0,
            "spo2": 98.0,
            "sleep_hours": 7.8,
            "activity_steps": 9100.0,
            "bmi": 23.2,
            "stress_level": 3.0,
            "blood_pressure_systolic": 116.0,
            "blood_pressure_diastolic": 74.0,
            "sleep_efficiency": 87.0,
            "latest_observation_at": current_time,
        },
        "histories": {
            "heart_rate": [62.0, 63.0, 64.0, 63.0, 64.0, 62.0],
            "sleep": [7.2, 7.5, 7.7, 7.6, 7.8, 7.8],
            "spo2": [97.0, 97.0, 98.0, 98.0, 97.0, 98.0],
            "blood_pressure_systolic": [118.0, 117.0, 116.0, 116.0],
            "blood_pressure_diastolic": [77.0, 76.0, 75.0, 74.0],
            "fatigue_proxy": [9.0, 7.5, 6.0, 5.5],
        },
        "timestamps": {
            "heart_rate": current_time,
            "spo2": current_time,
            "sleep_hours": current_time,
        },
        "source_coverage": {
            "wearable": True,
            "sleep": True,
            "cardio": True,
            "respiratory": True,
            "metabolic": True,
        },
        "row_count": 24,
    }


def _lab_signals(now: datetime | None = None) -> dict[str, object]:
    current_time = now or datetime.now(timezone.utc)
    return {
        "current": {
            "glucose": 92.0,
            "hba1c": 5.3,
            "cholesterol": 168.0,
            "triglycerides": 128.0,
            "crp": 2.4,
        },
        "histories": {
            "glucose": [96.0, 94.0, 93.0, 92.0],
        },
        "details": {},
        "source_coverage": {"labs": True, "glucose": True, "lipids": True},
        "row_count": 4,
        "latest_observation_at": current_time,
    }


def test_scoring_engine_is_deterministic_for_same_inputs():
    baseline = _baseline()
    wearable = _wearable_signals()
    labs = _lab_signals()

    first = ScoringEngine.score(
        user_id="user-1",
        source="test",
        window="24h",
        wearable_signals=wearable,
        lab_signals=labs,
        baseline_profile=baseline,
        previous_scores=[76.0, 77.5, 78.0],
    )
    second = ScoringEngine.score(
        user_id="user-1",
        source="test",
        window="24h",
        wearable_signals=wearable,
        lab_signals=labs,
        baseline_profile=baseline,
        previous_scores=[76.0, 77.5, 78.0],
    )

    assert first.score == second.score
    assert first.trend == second.trend
    assert first.confidence == second.confidence
    assert first.category_scores["cardiovascular_score"].score >= 80
    assert first.category_scores["sleep_score"].score >= 80


def test_anomaly_detector_flags_hr_spike_and_oxygen_drop():
    baseline = _baseline()
    anomalies = AnomalyDetector.detect(
        current={
            "heart_rate": 78.0,
            "spo2": 92.5,
            "sleep_hours": 5.8,
            "recovery_proxy": 48.0,
        },
        histories={
            "blood_pressure_systolic": [118.0, 140.0, 121.0, 139.0],
            "blood_pressure_diastolic": [75.0, 92.0, 78.0, 90.0],
            "fatigue_proxy": [8.0, 13.0, 19.0],
        },
        baseline=baseline,
        timestamps={"heart_rate": datetime.now(timezone.utc)},
    )

    types = {item["type"] for item in anomalies}
    assert "hr_spike" in types
    assert "oxygen_drop" in types
    assert "sleep_degradation" in types
    assert "bp_instability" in types
    assert "fatigue_trend" in types


def test_baseline_engine_adapts_to_recent_history():
    existing_row = SimpleNamespace(
        metric_name="sleep_hours",
        mean_7d=7.0,
        mean_30d=7.0,
        std_dev=0.3,
        sample_count=10,
        window_start=None,
        window_end=None,
        metric_payload={"source": "existing"},
    )
    profile = BaselineEngine.build_from_histories(
        user_id="user-1",
        histories={
            "sleep_hours": [6.8, 7.0, 7.2, 7.4, 7.6, 7.8, 8.0],
            "resting_hr": [60.0, 59.0, 58.0, 58.0, 57.0],
        },
        existing_rows=[existing_row],
    )

    assert profile.metrics["sleep_hours"].mean_7d == 7.4
    assert profile.metrics["resting_hr"].mean_7d == 58.4
    assert profile.metrics["sleep_hours"].sample_count == 7


def test_trend_engine_distinguishes_improving_and_volatile_states():
    improving = TrendEngine.classify([78.0, 76.0, 74.0, 72.0], lower_is_better=True)
    volatile = TrendEngine.classify([70.0, 90.0, 68.0, 92.0], lower_is_better=False)

    assert improving["direction"] == "improving"
    assert volatile["direction"] == "volatile"


def test_confidence_engine_rewards_coverage_and_recency():
    high = ConfidenceEngine.score(
        source_coverage={"wearable": True, "labs": True, "baseline": True, "profile": True},
        sample_count=32,
        anomaly_count=0,
        latest_observation_at=datetime.now(timezone.utc) - timedelta(hours=2),
        baseline_sample_count=30,
    )
    low = ConfidenceEngine.score(
        source_coverage={"wearable": False, "labs": False, "baseline": True, "profile": False},
        sample_count=2,
        anomaly_count=3,
        latest_observation_at=datetime.now(timezone.utc) - timedelta(days=9),
        baseline_sample_count=2,
    )

    assert high > low
    assert high >= 0.75
    assert low <= 0.45


def test_realtime_event_listener_delegates_to_scheduler():
    db = SimpleNamespace()
    user = SimpleNamespace(id="user-1")

    with patch("ai.scoring.realtime.event_listener.ScoreScheduler.run_now", return_value={"score": 81.2}) as run_now:
        payload = ScoringEventListener.on_wearable_sync(db, user)

    assert payload["score"] == 81.2
    run_now.assert_called_once_with(db, user, trigger="wearable_sync", window="24h")
