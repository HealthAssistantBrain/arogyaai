from __future__ import annotations

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

from pipelines.storage_pipeline.service import StoragePipelineService
from services import dashboard_service
from services.dashboard_realtime import _dashboard_flat_contract
from services.prediction_explanation_service import PredictionExplanationService
from workers import preventive_worker


def test_dashboard_flat_contract_keeps_preventive_slice_and_flattens_prevention():
    bundle = {
        "preventive": {
            "data": {
                "guidance": {"headline": "Recovery is asking for earlier support"},
                "monitoring": {"overall_risk": 63.0},
                "alerts": [{"alert_id": "a1", "title": "Recovery needs preventive attention"}],
            },
            "last_updated": "2026-05-11T00:00:00+00:00",
        }
    }

    flat = _dashboard_flat_contract(bundle)

    assert flat["preventive"]["data"]["guidance"]["headline"] == "Recovery is asking for earlier support"
    assert flat["prevention"]["monitoring"]["overall_risk"] == 63.0


def test_storage_pipeline_normalizes_prevention_and_forecasting():
    payload = StoragePipelineService._normalize_health_insights_payload(
        {
            "risk": {"overall_risk_score": 44.0},
            "drivers": [],
            "recommendations": [],
            "availability": {"has_wearable": True},
            "prevention": {"guidance": {"headline": "Watch recovery"}},
            "forecasting": {"forecast": {"72h": {"summary": "watchful"}}},
        }
    )

    assert payload["prevention"]["guidance"]["headline"] == "Watch recovery"
    assert payload["forecasting"]["forecast"]["72h"]["summary"] == "watchful"


def test_dashboard_service_merges_preventive_alerts_without_duplicates():
    user = SimpleNamespace(id="user-1")
    merged = dashboard_service._merge_preventive_alerts(
        [
            {
                "id": "base-1",
                "title": "Existing alert",
                "severity": "warning",
            }
        ],
        {
            "alerts": [
                {
                    "alert_id": "preventive-1",
                    "title": "Recovery needs preventive attention",
                    "message": "Recovery is slipping.",
                    "severity": "warning",
                    "guidance": ["Protect sleep"],
                    "created_at": "2026-05-11T00:00:00+00:00",
                },
                {
                    "alert_id": "preventive-2",
                    "title": "Existing alert",
                    "message": "Duplicate title should be skipped.",
                    "severity": "warning",
                    "created_at": "2026-05-11T00:00:00+00:00",
                },
            ]
        },
        user,
    )

    assert len(merged) == 2
    assert merged[-1]["alert_type"] == "preventive_alert"
    assert merged[-1]["action_label"] == "Protect sleep"


def test_prediction_explanation_safe_attach_adds_prevention(monkeypatch):
    monkeypatch.setattr(
        "services.prediction_explanation_service._preventive_engine",
        SimpleNamespace(generate=lambda *args, **kwargs: {"monitoring": {"overall_risk": 61.0}}),
    )
    payload = PredictionExplanationService._attach_recommendation_plans_safe(
        MagicMock(),
        SimpleNamespace(id="user-1"),
        {"recommendation_plan": {"summary": "Existing plan"}},
    )

    assert payload["prevention"]["monitoring"]["overall_risk"] == 61.0


def test_dashboard_alert_endpoint_includes_preventive_payload(monkeypatch):
    monkeypatch.setattr(
        dashboard_service,
        "get_active_alerts",
        lambda user, db: asyncio.sleep(0, result={"success": True, "status": "ready", "source": "db", "error": None, "data": {"alerts": []}}),
    )
    monkeypatch.setattr(
        dashboard_service,
        "_preventive_engine",
        SimpleNamespace(generate=lambda *args, **kwargs: {"alerts": [{"alert_id": "p1", "title": "Recovery needs preventive attention", "message": "Recovery is slipping.", "severity": "warning", "guidance": ["Protect sleep"], "created_at": "2026-05-11T00:00:00+00:00"}], "generated_at": "2026-05-11T00:00:00+00:00"}),
    )

    result = asyncio.run(dashboard_service.get_alerts(SimpleNamespace(id="user-1"), MagicMock()))

    assert result["data"]["alerts"][0]["alert_type"] == "preventive_alert"
    assert result["last_updated"] == "2026-05-11T00:00:00+00:00"


def test_preventive_worker_runs_autonomous_scan(monkeypatch):
    @contextmanager
    def _fake_session_scope(*args, **kwargs):
        yield MagicMock()

    class _FakeEngine:
        def generate(self, db, user, *, force_refresh=False, persist=True):
            assert force_refresh is False
            assert persist is True
            return {
                "monitoring": {"overall_risk": 62.0},
                "alerts": [{"alert_id": f"preventive-{user.id}"}],
            }

    monkeypatch.setattr(preventive_worker, "session_scope", _fake_session_scope)
    monkeypatch.setattr(preventive_worker, "PreventiveEngine", _FakeEngine)
    monkeypatch.setattr(preventive_worker, "_load_candidate_user_ids", lambda db: ["user-1", "missing"])
    monkeypatch.setattr(
        preventive_worker,
        "_load_user",
        lambda db, user_id: None if user_id == "missing" else SimpleNamespace(id=user_id),
    )
    monkeypatch.setattr(preventive_worker, "log_pool_snapshot", lambda force=False: None)
    preventive_worker._worker_stop.clear()

    summary = preventive_worker.run_preventive_monitoring_once()

    assert summary["status"] == "ready"
    assert summary["processed_users"] == 1
    assert summary["skipped_users"] == 1
    assert summary["failed_users"] == 0
    assert summary["alerts_generated"] == 1
