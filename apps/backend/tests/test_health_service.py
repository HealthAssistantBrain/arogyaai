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
    async def _check_database_side_effect(*args, label: str, **kwargs):
        if label == "primary_db":
            return {"status": "ok", "target": label}
        await asyncio.sleep(0.05)
        return {"status": "ok", "target": label}

    async def _slow_timescale(*args, **kwargs):
        await asyncio.sleep(0.05)
        return {"status": "ok", "provider": "neon"}

    with patch.object(health_service, "analytics_runtime_enabled", return_value=True), patch.object(
        health_service,
        "_check_database",
        AsyncMock(side_effect=_check_database_side_effect),
    ), patch.object(
        health_service,
        "_check_redis",
        AsyncMock(return_value={"status": "ok"}),
    ), patch.object(
        health_service,
        "_check_http_service",
        AsyncMock(return_value={"status": "ok"}),
    ), patch.object(
        health_service,
        "_fetch_timescale_status",
        AsyncMock(side_effect=_slow_timescale),
    ), patch.object(
        health_service,
        "get_qdrant_health",
        AsyncMock(return_value={"status": "healthy", "mode": "local"}),
    ), patch.object(
        health_service,
        "OPTIONAL_PROBE_BUDGET_SECONDS",
        0.01,
    ):
        payload = asyncio.run(health_service.get_system_readiness())

    assert payload["status"] == "ok"
    assert payload["core_system"] == "healthy"
    assert payload["services"]["qdrant"] == "ok"
    assert payload["services"]["analytics_db"] == "degraded"
    assert payload["services"]["timescale"] == "degraded"
    assert payload["checks"]["analytics_db"]["error"] == "probe_budget_exceeded"
    assert payload["checks"]["timescale"]["error"] == "probe_budget_exceeded"
