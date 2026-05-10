from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import sys

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

from services.disease_simulation_service import DiseaseSimulationService, SimulatorInputs


def test_simulation_recomputes_multi_condition_risk_and_insights():
    baseline_context = {
        "baseline": SimulatorInputs(
            sleep=6.0,
            steps=4200,
            heart_rate=88,
            systolic_bp=142,
            diastolic_bp=92,
            weight=86.0,
        ),
        "profile": {
            "age": 46,
            "height_cm": 172.0,
            "weight_kg": 86.0,
            "bmi": 29.1,
        },
        "feature_snapshot": {
            "sleep_duration": 6.0,
            "activity_level": 4200,
            "avg_rhr": 88.0,
            "hr_mean_7d": 88.0,
            "systolic_bp": 142,
            "diastolic_bp": 92,
            "glucose": 108.0,
            "bmi": 29.1,
            "height_cm": 172.0,
        },
        "conditions": ["Hypertension"],
        "focus_options": ["cardiovascular", "diabetes", "respiratory"],
        "assumptions": ["Uses feature snapshot baseline."],
    }
    payload = SimpleNamespace(
        focus_condition="cardiovascular",
        timeframe_months=6,
        simulation=SimpleNamespace(
            model_dump=lambda: {
                "sleep": 8.0,
                "steps": 10500,
                "heart_rate": 70,
                "systolic_bp": 120,
                "diastolic_bp": 78,
                "weight": 78.0,
            }
        ),
    )
    shap_values = [
        {
            "feature_name": "steps_avg_7d",
            "shap_value": 0.19,
            "abs_shap_value": 0.19,
            "direction": "increase",
            "shap_payload": {"feature_value": 10500},
        }
    ]

    with patch.object(DiseaseSimulationService, "build_baseline", return_value=baseline_context), \
        patch.object(DiseaseSimulationService, "_latest_profile", return_value=SimpleNamespace(height_cm=172.0, weight_kg=86.0, age=46)), \
        patch.object(
            DiseaseSimulationService,
            "_predict_with_model",
            side_effect=[
                (0.72, shap_values, "rf-v1"),
                (0.34, shap_values, "rf-v1"),
            ],
        ), patch("services.disease_simulation_service.trigger_notification_sync") as trigger_notification:
        result = DiseaseSimulationService.simulate(MagicMock(), SimpleNamespace(id="user-1"), payload)

    data = result["data"]
    assert result["source"] == "hybrid_ml_plus_rules"
    assert data["simulated_risk"]["cardiovascular"] < data["current_risk"]["cardiovascular"]
    assert data["risk_comparison"][0]["delta"] < 0
    assert data["outcome"]["headline"]
    assert data["structured_sections"][0]["title"] == "Scenario Overview"
    assert data["rendering"]["charts"][0]["id"] == "risk-comparison"
    assert "Type 2 diabetes risk" in data["possible_conditions"]
    assert any(item["feature"] == "glucose" for item in data["recommendations"])
    assert data["key_drivers"]
    trigger_notification.assert_called_once()
