from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import sys

import numpy as np

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


def test_health_engine_passes_numpy_matrix_to_shap():
    engine = HealthEngine()
    shap_input: dict[str, object] = {}
    payload = {
        "hr_mean_7d": 72,
        "steps_avg_7d": 5400,
        "sleep_efficiency": 78,
    }

    class _FakeShapValues:
        values = np.array([[0.1, -0.2, 0.3]])

    class _FakeExplainer:
        def __init__(self, raw_model):
            self.raw_model = raw_model

        def __call__(self, X):
            shap_input["X"] = X
            return _FakeShapValues()

    fake_shap = SimpleNamespace(Explainer=_FakeExplainer)

    with patch.dict(sys.modules, {"shap": fake_shap}):
        drivers = engine.compute_drivers(object(), payload)

    X = shap_input["X"]
    assert isinstance(X, np.ndarray)
    assert X.shape == (1, len(engine._vectorize(payload)))
    assert drivers == [[0.1, -0.2, 0.3]]


def test_fetch_health_insights_normalizes_partial_payload():
    db = _mock_db_for_lab(has_lab=False)
    user = SimpleNamespace(id="user-1")
    latest_risk = SimpleNamespace(
        id="prediction-1",
        risk_payload={
            "recommendations": ["Stay active"],
            "rag_explanation": {
                "payload": {
                    "summary": "Explainable risk summary",
                    "sources": [],
                }
            },
        },
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
    assert payload["explanation"] == {
        "summary": "Explainable risk summary",
        "sources": [],
    }
    assert payload["availability"] == {
        "has_wearable": True,
        "has_lab": False,
        "has_baseline": False,
    }


def test_insights_service_surfaces_cached_explanation():
    with patch.object(
        StoragePipelineService,
        "fetch_health_insights",
        return_value={
            "risk": {"overall_risk_score": 31.5},
            "drivers": [],
            "analysis": "Stored analysis",
            "explanation": {"summary": "Stored explanation"},
            "recommendations": ["Stay active"],
            "confidence": 0.8,
            "data_points": 4,
            "feature_snapshot": {},
            "last_updated": "2026-04-30T00:00:00+00:00",
        },
    ):
        payload = InsightsService.get_insights(MagicMock(), SimpleNamespace(id="user-1"))

    assert payload["success"] is True
    assert payload["data"]["explanation"]["summary"] == "Stored explanation."
    assert payload["data"]["explanation"]["clinical_report"]["summary"] == "Stored explanation."


def test_health_insights_service_returns_safe_empty_contract_when_missing():
    with patch.object(StoragePipelineService, "fetch_health_insights", return_value=None):
        payload = InsightsService.get_health_insights(MagicMock(), SimpleNamespace(id="user-1"))

    assert payload["success"] is True
    assert payload["status"] == "fallback"
    assert payload["data"]["risk_scores"] == {}
    assert payload["data"]["drivers"] == []
    assert payload["data"]["insights"] == []
    assert payload["data"]["recommendations"] == ["No data available yet"]


def test_health_insights_service_builds_dashboard_insights():
    with patch.object(
        StoragePipelineService,
        "fetch_health_insights",
        return_value={
            "risk": {"overall_risk_score": 31.5},
            "drivers": [
                {
                    "label": "Elevated Resting Heart Rate",
                    "value": 88,
                    "detail": "Resting heart rate is above the recent recovery target.",
                }
            ],
            "recommendations": ["Prioritize sleep, hydration, and a lighter training day."],
            "availability": {"has_wearable": True, "has_lab": False, "has_baseline": True},
            "last_updated": "2026-04-30T00:00:00+00:00",
        },
    ):
        payload = InsightsService.get_health_insights(MagicMock(), SimpleNamespace(id="user-1"))

    assert payload["success"] is True
    assert payload["status"] == "ready"
    assert payload["data"]["insights"] == [
        {
            "title": "Elevated Resting Heart Rate",
            "value": "88",
            "description": "Resting heart rate is above the recent recovery target.",
            "recommendation": "Prioritize sleep, hydration, and a lighter training day.",
        }
    ]
