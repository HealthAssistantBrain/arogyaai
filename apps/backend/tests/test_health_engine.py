from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.health_engine import HealthEngine
from services.insights_service import InsightsService
from pipelines.storage_pipeline.service import StoragePipelineService


class _PredictModel:
    def predict(self, values):
        return [0.42, 0.11]


def _mock_db_for_lab(has_lab: bool = False) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = object() if has_lab else None
    return db


def test_health_engine_returns_safe_defaults_for_missing_model_and_data():
    engine = HealthEngine()

    assert engine.compute_risk(None, {}) == {}
    assert engine.compute_drivers(None, {}) == []
    assert engine.generate_recommendations([]) == ["Maintain current healthy lifestyle"]


def test_health_engine_computes_risk_from_predict_model():
    engine = HealthEngine()

    risk = engine.compute_risk(
        _PredictModel(),
        {
            "hr_mean_7d": 72,
            "steps_avg_7d": 5400,
            "sleep_efficiency": 78,
        },
    )

    assert risk == {
        "cardio_risk": 0.42,
        "diabetes_risk": 0.11,
    }


def test_fetch_health_insights_normalizes_partial_payload():
    db = _mock_db_for_lab(has_lab=False)
    user = SimpleNamespace(id="user-1")
    latest_risk = SimpleNamespace(
        id="prediction-1",
        risk_payload={"recommendations": ["Stay active"]},
        overall_score=31.5,
        risk_level=SimpleNamespace(value="MODERATE"),
        confidence_score=None,
        feature_snapshot={"source_breakdown": {"step_points": 3}},
        calculated_at=None,
    )

    with patch.object(StoragePipelineService, "latest_risk_score", return_value=latest_risk), patch.object(
        StoragePipelineService,
        "latest_shap_values",
        return_value=[],
    ), patch.object(
        StoragePipelineService,
        "latest_feature_snapshot",
        return_value=SimpleNamespace(feature_payload={"source_breakdown": {"step_points": 3}}),
    ), patch.object(
        StoragePipelineService,
        "latest_baseline_metrics",
        return_value=[],
    ):
        payload = StoragePipelineService.fetch_health_insights(db, user)

    assert payload is not None
    assert payload["risk"]["overall_risk_score"] == 31.5
    assert payload["risk"]["risk_level"] == "MODERATE"
    assert payload["drivers"] == []
    assert payload["recommendations"] == ["Stay active"]
    assert payload["availability"] == {
        "has_wearable": True,
        "has_lab": False,
        "has_baseline": False,
    }


def test_health_insights_service_returns_safe_empty_contract_when_missing():
    with patch.object(StoragePipelineService, "fetch_health_insights", return_value=None):
        payload = InsightsService.get_health_insights(MagicMock(), SimpleNamespace(id="user-1"))

    assert payload["success"] is True
    assert payload["status"] == "fallback"
    assert payload["data"]["risk_scores"] == {}
    assert payload["data"]["drivers"] == []
    assert payload["data"]["recommendations"] == ["No data available yet"]
