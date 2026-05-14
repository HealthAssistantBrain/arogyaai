from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import sys

import pytest

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

from cache.recommendations.service import RecommendationSnapshotService
from core.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError
from integrations.googlefit.cache import (
    AVAILABILITY_REASON_EMPTY,
    AVAILABILITY_REASON_UNSUPPORTED,
    GoogleFitAvailabilityCache,
    GoogleFitMetricRegistry,
)
from dashboard_realtime.connection_manager import DashboardConnectionManager


class DummyWebSocket:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.closed = False

    async def accept(self) -> None:
        return None

    async def close(self, code: int | None = None, reason: str | None = None) -> None:
        self.closed = True

    async def send_text(self, message: str) -> None:
        self.messages.append(message)


def test_google_fit_unsupported_metric_cache_suppresses_queries():
    user_id = f"user-{uuid4()}"

    record = asyncio.run(
        GoogleFitAvailabilityCache.set(
            user_id,
            "spo2",
            reason=AVAILABILITY_REASON_UNSUPPORTED,
            detail="unsupported metric",
        )
    )
    should_query, cached_record = asyncio.run(GoogleFitMetricRegistry.should_query(user_id, "spo2"))

    assert should_query is False
    assert cached_record is not None
    assert cached_record.reason == AVAILABILITY_REASON_UNSUPPORTED
    assert record.cooldown_seconds == 24 * 60 * 60


def test_google_fit_empty_metric_uses_shorter_cooldown():
    user_id = f"user-{uuid4()}"

    record = asyncio.run(
        GoogleFitAvailabilityCache.set(
            user_id,
            "sleep",
            reason=AVAILABILITY_REASON_EMPTY,
            detail="empty dataset",
        )
    )
    should_query, cached_record = asyncio.run(GoogleFitMetricRegistry.should_query(user_id, "sleep"))

    assert should_query is False
    assert cached_record is not None
    assert record.cooldown_seconds == 30 * 60


def test_circuit_breaker_opens_and_recovers():
    breaker = CircuitBreaker("google-fit:test", failure_threshold=2, recovery_timeout_seconds=5)

    breaker.before_call()
    breaker.record_failure(RuntimeError("first"))
    breaker.record_failure(RuntimeError("second"))

    with pytest.raises(CircuitOpenError):
        breaker.before_call()

    breaker._state.opened_until = time.monotonic() - 1
    breaker.before_call()
    breaker.record_success()
    breaker.before_call()


def test_dashboard_connection_manager_emits_patch_after_primed_snapshot():
    socket = DummyWebSocket()
    manager = DashboardConnectionManager()

    asyncio.run(manager.connect("user-1", socket))
    asyncio.run(
        manager.prime_snapshot(
            "user-1",
            {
                "steps": {"value": 1200},
                "googleFit": {"data": {"connected": True}},
                "last_updated": "2026-05-12T10:00:00+00:00",
            },
        )
    )
    asyncio.run(
        manager.broadcast_snapshot(
            "user-1",
            {
                "steps": {"value": 1850},
                "googleFit": {"data": {"connected": True}},
                "last_updated": "2026-05-12T10:05:00+00:00",
            },
        )
    )

    assert len(socket.messages) == 1
    payload = json.loads(socket.messages[0])
    assert payload["type"] == "dashboard.patch"
    assert payload["data"]["steps"]["value"] == 1850
    assert payload["meta"]["full_reload"] is False
    assert "steps" in payload["meta"]["changed_keys"]


def test_recommendation_snapshot_get_snapshot_serves_cache_and_queues_refresh(monkeypatch):
    stale_snapshot = {
        "user_id": "user-1",
        "prediction_id": "pred-1",
        "last_updated": "2026-05-12T00:00:00+00:00",
        "explanation": {"data": {"prediction_id": "pred-1"}},
        "health_metrics": {"data": {"metrics": {}}},
        "score_snapshot": {"health_score": 81},
        "trend_metadata": {},
    }
    refresh_mock = AsyncMock()

    monkeypatch.setattr(RecommendationSnapshotService, "_is_stale", classmethod(lambda cls, snapshot: True))
    monkeypatch.setattr("cache.recommendations.service.RecommendationSnapshotStore.get", AsyncMock(return_value=stale_snapshot))
    monkeypatch.setattr("cache.recommendations.service.RecommendationSnapshotStore.get_stale", AsyncMock(return_value=None))
    monkeypatch.setattr(RecommendationSnapshotService, "ensure_refresh", refresh_mock)

    payload = asyncio.run(
        RecommendationSnapshotService.get_snapshot(
            db=None,
            user=SimpleNamespace(id="user-1"),
            prediction_id="pred-1",
        )
    )

    assert payload["status"] == "ready"
    assert payload["data"]["score_snapshot"]["health_score"] == 81
    assert payload["meta"]["refresh_queued"] is True
    refresh_mock.assert_awaited_once()


def test_recommendation_snapshot_get_snapshot_returns_fast_fallback_when_empty(monkeypatch):
    refresh_mock = AsyncMock()
    set_mock = AsyncMock()

    monkeypatch.setattr("cache.recommendations.service.RecommendationSnapshotStore.get", AsyncMock(return_value=None))
    monkeypatch.setattr("cache.recommendations.service.RecommendationSnapshotStore.get_stale", AsyncMock(return_value=None))
    monkeypatch.setattr("cache.recommendations.service.RecommendationSnapshotStore.set", set_mock)
    monkeypatch.setattr(RecommendationSnapshotService, "ensure_refresh", refresh_mock)

    payload = asyncio.run(
        RecommendationSnapshotService.get_snapshot(
            db=None,
            user=SimpleNamespace(id="user-1"),
            prediction_id=None,
        )
    )

    assert payload["status"] == "ready"
    assert payload["meta"]["refresh_queued"] is True
    assert payload["data"]["prediction_id"] is None
    assert payload["data"]["explanation"]["data"]["recommendation_plans"]
    set_mock.assert_awaited_once()
    refresh_mock.assert_awaited_once()


def test_fallback_explanation_payload_exposes_all_plan_aliases():
    plans = [{
        "condition": "Hypertension prevention plan",
        "risk_level": "MEDIUM",
        "summary": "Monitor BP and lifestyle consistency.",
    }]

    payload = RecommendationSnapshotService._fallback_explanation_payload(
        user_id="user-1",
        prediction_id="pred-1",
        plans=plans,
        tests=[{"test_name": "Lipid panel", "reason": "Check cardiovascular risk"}],
    )

    assert payload["prediction_id"] == "pred-1"
    assert payload["predictionId"] == "pred-1"
    assert payload["summary"] == "Monitor BP and lifestyle consistency."
    assert payload["source"] == "deterministic_fallback"
    assert payload["recommendation_plans"] == plans
    assert payload["recommendationPlans"] == plans
    assert payload["recommendations"] == plans
    assert payload["plans"] == plans
    assert payload["cards"] == plans
    assert payload["recommendation_items"][0]["title"] == "Lipid panel"
    assert payload["followUpRecommendations"][0]["description"] == "Check cardiovascular risk"
    assert payload["generated_at"]
    assert payload["generatedAt"]


def test_recommendation_snapshot_fallback_envelope_keeps_contract_aliases(monkeypatch):
    refresh_mock = AsyncMock()
    set_mock = AsyncMock()

    monkeypatch.setattr("cache.recommendations.service.RecommendationSnapshotStore.get", AsyncMock(return_value=None))
    monkeypatch.setattr("cache.recommendations.service.RecommendationSnapshotStore.get_stale", AsyncMock(return_value=None))
    monkeypatch.setattr("cache.recommendations.service.RecommendationSnapshotStore.set", set_mock)
    monkeypatch.setattr(RecommendationSnapshotService, "ensure_refresh", refresh_mock)

    payload = asyncio.run(
        RecommendationSnapshotService.get_snapshot(
            db=None,
            user=SimpleNamespace(id="user-1"),
            prediction_id="pred-2",
        )
    )

    explanation = payload["data"]["explanation"]["data"]

    assert payload["meta"]["refresh_queued"] is True
    assert explanation["recommendation_plans"]
    assert explanation["recommendationPlans"] == explanation["recommendation_plans"]
    assert explanation["recommendations"] == explanation["recommendation_plans"]
    assert explanation["cards"] == explanation["recommendation_plans"]
    assert explanation["prediction_id"] == "pred-2"
    assert explanation["predictionId"] == "pred-2"
