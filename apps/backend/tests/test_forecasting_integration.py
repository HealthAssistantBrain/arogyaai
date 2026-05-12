from __future__ import annotations

import asyncio
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

from pipelines.storage_pipeline.service import StoragePipelineService
from services import dashboard_service
from services.dashboard_realtime import _dashboard_flat_contract
from services.insights_service import InsightsService


def _mock_db_for_lab(has_lab: bool = False) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = object() if has_lab else None
    return db


def test_fetch_health_insights_includes_latest_forecasting_payload():
    db = _mock_db_for_lab(has_lab=False)
    user = SimpleNamespace(id="user-1")
    latest_risk = SimpleNamespace(
        id="prediction-1",
        risk_payload={"recommendations": ["Stay active"], "forecasting": {"source": "risk_payload"}},
        overall_score=31.5,
        risk_level=SimpleNamespace(value="MODERATE"),
        confidence_score=0.66,
        feature_snapshot={"source_breakdown": {"step_points": 3}},
        calculated_at=None,
    )
    latest_health = SimpleNamespace(
        health_payload={"forecasting": {"source": "health_payload", "forecast": {"24h": {"summary": "watch"}}}},
    )

    with patch.object(StoragePipelineService, "latest_risk_score", return_value=latest_risk), patch.object(
        StoragePipelineService,
        "latest_health_score",
        return_value=latest_health,
    ), patch.object(
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
    ), patch.object(
        StoragePipelineService,
        "latest_clinical_history",
        return_value=None,
    ):
        payload = StoragePipelineService.fetch_health_insights(db, user)

    assert payload is not None
    assert payload["forecasting"]["source"] == "health_payload"


def test_health_forecast_service_wraps_engine_payload():
    user = SimpleNamespace(id="user-1")
    db = MagicMock()

    with patch.object(
        dashboard_service,
        "_forecasting_engine",
        SimpleNamespace(generate=lambda *args, **kwargs: {"status": "ready", "source": "forecasting_engine", "forecast": {"24h": {}}, "confidence": 0.71}),
    ):
        payload = asyncio.run(dashboard_service.get_health_forecast(user, db))

    assert payload["success"] is True
    assert payload["data"]["forecast"]["24h"] == {}
    assert payload["source"] == "forecasting_engine"


def test_insights_service_surfaces_forecasting_context():
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
            "forecasting": {"forecast": {"24h": {"summary": "watch"}}},
            "last_updated": "2026-04-30T00:00:00+00:00",
        },
    ):
        payload = InsightsService.get_insights(MagicMock(), SimpleNamespace(id="user-1"))

    assert payload["success"] is True
    assert payload["data"]["forecasting"]["forecast"]["24h"]["summary"] == "watch"


def test_dashboard_flat_contract_keeps_forecast_for_frontend_cards():
    flat = _dashboard_flat_contract(
        {
            "forecast": {
                "data": {
                    "forecast": {
                        "24h": {"summary": "watchful"}
                    }
                }
            },
            "prediction": {"data": {"recommendations": []}},
            "history": {"data": {"sleep": []}},
            "recommendedTests": {"data": []},
            "vitals": {},
            "healthScore": {"data": {"score": 78}},
        }
    )

    assert flat["forecast"]["forecast"]["24h"]["summary"] == "watchful"
