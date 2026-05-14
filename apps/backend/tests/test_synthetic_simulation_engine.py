from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
import sys
from uuid import uuid4

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-placeholder")
os.environ.setdefault("APP_ENCRYPTION_KEY", "test-encryption-key-not-placeholder")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-supabase-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-supabase-service-role-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/arogyaai_test")

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from ai.simulation import SimulationEngine, SimulationRequest
from ai.simulation.core.event_generator import EventGenerator
from ai.simulation.core.physiology_orchestrator import PhysiologyOrchestrator
from ai.simulation.core.synthetic_population import SyntheticPopulation


def test_simulation_engine_generates_contract_and_correlated_signals():
    engine = SimulationEngine()
    result = engine.generate(
        SimulationRequest(
            population_size=2,
            duration_days=5,
            lookback_hours=12,
            horizon_hours=6,
            seed=9,
        )
    )

    assert result.dataset_contract.schema_version == "synthetic-medical-contract.v1"
    assert result.records
    assert result.temporal_windows
    assert set(result.records[0].keys()) >= {
        "user_id",
        "timestamp",
        "signal_type",
        "signal_name",
        "value",
        "unit",
        "confidence",
        "baseline_delta",
        "anomaly_score",
        "risk_level",
        "physiological_state",
        "recovery_state",
        "trend_direction",
        "synthetic_profile",
        "demographic_profile",
        "trajectory_phase",
        "source",
        "labels",
        "metadata",
    }

    points = result.sequences[0].state_points
    sorted_points = sorted((point for point in points if point["hrv"] is not None), key=lambda item: item["stress_index"])
    quartile = max(4, len(sorted_points) // 4)
    low_stress_hrv = [point["hrv"] for point in sorted_points[:quartile]]
    high_stress_hrv = [point["hrv"] for point in sorted_points[-quartile:]]
    assert sum(high_stress_hrv) / len(high_stress_hrv) < sum(low_stress_hrv) / len(low_stress_hrv)


def test_hypertensive_profile_progresses_with_higher_bp_load_over_time():
    profile = SyntheticPopulation.build_profile(profile_name="hypertensive", user_id="hyper-1", seed=5).model_dump(mode="json")
    start_at = datetime(2026, 1, 1, tzinfo=UTC)
    schedule = EventGenerator.generate(profile, start_at.date(), 7)
    points = PhysiologyOrchestrator.generate_sequence(
        profile=profile,
        start_at=start_at,
        hours=24 * 7,
        event_schedule=schedule,
        inject_anomalies=False,
    )

    first_bp = sum(point["blood_pressure_systolic"] for point in points[:24]) / 24.0
    last_bp = sum(point["blood_pressure_systolic"] for point in points[-24:]) / 24.0
    assert last_bp >= first_bp
    assert points[-1]["state"]["bp_load"] >= points[0]["state"]["bp_load"]


def test_anomaly_injection_produces_labels_and_sensor_failures():
    profile = SyntheticPopulation.build_profile(profile_name="shift_worker", user_id="shift-1", seed=14).model_dump(mode="json")
    start_at = datetime(2026, 2, 1, tzinfo=UTC)
    schedule = EventGenerator.generate(profile, start_at.date(), 5)
    points = PhysiologyOrchestrator.generate_sequence(
        profile=profile,
        start_at=start_at,
        hours=24 * 5,
        event_schedule=schedule,
        inject_anomalies=True,
    )

    anomaly_points = [point for point in points if point["anomaly_score"] > 0.0]
    failed_points = [point for point in points if point.get("sensor_failures")]
    assert anomaly_points
    assert any(point["anomaly_labels"] for point in anomaly_points)
    assert failed_points
    assert all(point["hrv"] is None and point["spo2"] is None for point in failed_points)


def test_feature_vectors_and_temporal_windows_are_ml_ready():
    result = SimulationEngine().generate(
        SimulationRequest(
            population_size=1,
            duration_days=4,
            lookback_hours=18,
            horizon_hours=6,
            seed=3,
        )
    )

    vector = result.feature_vectors[0]
    assert "heart_rate_mean_24h" in vector
    assert "glucose_trend_6h" in vector
    assert "future_recovery_target" in vector
    window = result.temporal_windows[0]
    assert len(window["sequence"]) == 18
    assert set(window["targets"].keys()) == {"risk_target", "future_recovery_target", "anomaly_target"}


def test_export_pipeline_writes_split_artifacts_and_manifests():
    export_root = REPO_ROOT / "data" / f"synthetic-datasets-{uuid4().hex[:8]}"
    result = SimulationEngine().generate(
        SimulationRequest(
            population_size=3,
            duration_days=3,
            export_root=str(export_root),
            lookback_hours=12,
            horizon_hours=6,
            seed=11,
        )
    )

    assert result.exports["train"]["rows"] > 0
    assert (export_root / "train" / "train.jsonl").exists()
    assert (export_root / "train" / "train.csv").exists()
    assert (export_root / "manifests" / "schema_manifest.json").exists()
    assert (export_root / "schemas" / "dataset_contract.json").exists()
    assert (export_root / "metadata" / "generation_metadata.json").exists()
