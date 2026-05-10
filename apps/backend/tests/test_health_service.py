from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services import health_service


def test_get_neon_health_reports_mode_and_read_strategy():
    with patch.object(health_service, "analytics_runtime_enabled", return_value=True), patch.object(
        health_service,
        "_check_database",
        AsyncMock(return_value={"status": "ok", "target": "analytics_db"}),
    ), patch.object(health_service, "analytics_reads_from_primary", return_value=True), patch.object(
        health_service,
        "ANALYTICS_DB_MODE",
        "dual_write",
    ):
        payload = asyncio.run(health_service.get_neon_health())

    assert payload["status"] == "ok"
    assert payload["provider"] == "neon"
    assert payload["mode"] == "dual_write"
    assert payload["read_strategy"] == "primary"
    assert payload["target"] == "analytics_db"
    assert payload["checked_at"]


def test_get_timescale_health_returns_hypertable_snapshot():
    with patch.object(
        health_service,
        "_fetch_timescale_status",
        AsyncMock(
            return_value={
                "status": "ok",
                "provider": "neon",
                "extension_version": "2.14.2",
                "hypertables": ["health_scores", "user_vitals", "wearable_metrics"],
                "continuous_aggregates": ["user_vitals_daily_summary"],
            }
        ),
    ):
        payload = asyncio.run(health_service.get_timescale_health())

    assert payload["status"] == "ok"
    assert payload["provider"] == "neon"
    assert payload["extension_version"] == "2.14.2"
    assert payload["hypertables"] == ["health_scores", "user_vitals", "wearable_metrics"]
    assert payload["continuous_aggregates"] == ["user_vitals_daily_summary"]
    assert payload["checked_at"]


def test_get_qdrant_health_adds_timestamp():
    with patch.object(
        health_service,
        "probe_qdrant_health",
        return_value={
            "status": "healthy",
            "mode": "cloud",
            "collection_name": "medical_knowledge",
        },
    ):
        payload = asyncio.run(health_service.get_qdrant_health())

    assert payload["status"] == "healthy"
    assert payload["mode"] == "cloud"
    assert payload["collection_name"] == "medical_knowledge"
    assert payload["checked_at"]


def test_get_system_readiness_degrades_slow_optional_analytics_without_marking_core_down():
    lifecycle_snapshot = {
        "phase": "tier2",
        "services": {
            "prediction_service": {"status": "ready", "tier": "tier2"},
            "rag_service": {"status": "ready", "tier": "tier2"},
            "analytics_db": {"status": "degraded", "tier": "tier2", "detail": "probe_timeout"},
            "timescale": {"status": "degraded", "tier": "tier2", "detail": "probe_timeout"},
            "qdrant": {"status": "warming", "tier": "tier2"},
            "ollama": {"status": "warming", "tier": "tier2"},
            "nvidia_provider": {"status": "deferred", "tier": "tier2"},
            "google_fit_worker": {"status": "deferred", "tier": "tier3"},
            "dashboard_listener": {"status": "deferred", "tier": "tier3"},
            "emergency_worker": {"status": "deferred", "tier": "tier3"},
        },
    }

    with patch.object(health_service, "_READINESS_CACHE", {"expires_at": 0.0, "payload": None}), patch.object(
        health_service,
        "_check_database",
        AsyncMock(return_value={"status": "ok", "target": "primary_db"}),
    ), patch.object(
        health_service,
        "_check_redis",
        AsyncMock(return_value={"status": "ok"}),
    ), patch.object(
        health_service,
        "get_supabase_auth_snapshot",
        return_value={"status": "warming", "cache_state": "empty"},
    ), patch.object(
        health_service.startup_lifecycle,
        "snapshot",
        return_value=lifecycle_snapshot,
    ):
        payload = asyncio.run(health_service.get_system_readiness())

    assert payload["status"] == "ok"
    assert payload["core_system"] == "healthy"
    assert payload["services"]["qdrant"] == "warming"
    assert payload["services"]["analytics_db"] == "degraded"
    assert payload["services"]["timescale"] == "degraded"
    assert payload["services"]["supabase_auth"] == "warming"
    assert payload["checks"]["analytics_db"]["detail"] == "probe_timeout"
    assert payload["checks"]["timescale"]["detail"] == "probe_timeout"


def test_get_system_readiness_keeps_stale_supabase_auth_healthy():
    lifecycle_snapshot = {
        "phase": "tier3",
        "services": {
            "prediction_service": {"status": "ready", "tier": "tier2"},
            "rag_service": {"status": "ready", "tier": "tier2"},
            "analytics_db": {"status": "skipped", "tier": "tier2"},
            "timescale": {"status": "skipped", "tier": "tier2"},
            "qdrant": {"status": "ready", "tier": "tier2"},
            "ollama": {"status": "warming", "tier": "tier2"},
            "nvidia_provider": {"status": "deferred", "tier": "tier2"},
            "google_fit_worker": {"status": "deferred", "tier": "tier3"},
            "dashboard_listener": {"status": "ready", "tier": "tier3"},
            "emergency_worker": {"status": "ready", "tier": "tier3"},
        },
    }

    with patch.object(health_service, "_READINESS_CACHE", {"expires_at": 0.0, "payload": None}), patch.object(
        health_service,
        "_check_database",
        AsyncMock(return_value={"status": "ok", "target": "primary_db"}),
    ), patch.object(
        health_service,
        "_check_redis",
        AsyncMock(return_value={"status": "ok"}),
    ), patch.object(
        health_service,
        "get_supabase_auth_snapshot",
        return_value={
            "status": "healthy",
            "cache_state": "stale",
            "last_fetch_error": "timed out",
            "startup_warmup_status": "ready",
        },
    ), patch.object(
        health_service.startup_lifecycle,
        "snapshot",
        return_value=lifecycle_snapshot,
    ):
        payload = asyncio.run(health_service.get_system_readiness())

    assert payload["status"] == "ok"
    assert payload["core_system"] == "healthy"
    assert payload["services"]["supabase_auth"] == "healthy"
    assert payload["checks"]["supabase_auth"]["cache_state"] == "stale"
