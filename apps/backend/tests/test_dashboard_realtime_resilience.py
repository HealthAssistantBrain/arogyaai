from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

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

from core.serialization.safe_response import websocket_send_json_safe
from dashboard_realtime.connection_manager import DashboardConnectionManager
from services import dashboard_realtime


class DummyWebSocket:
    def __init__(self, *, fail_send: bool = False, closed: bool = False) -> None:
        self.fail_send = fail_send
        self.closed = closed
        self.messages: list[str] = []

    async def accept(self) -> None:
        return None

    async def send_text(self, message: str) -> None:
        if self.fail_send:
            raise RuntimeError("Cannot call send once a close message has been sent.")
        self.messages.append(message)

    async def close(self, code: int | None = None, reason: str | None = None) -> None:
        self.closed = True


def test_websocket_send_json_safe_skips_closed_socket():
    socket = DummyWebSocket(closed=True)

    delivered = asyncio.run(
        websocket_send_json_safe(
            socket,
            {"type": "dashboard.update", "data": {"status": "ready"}},
            context="test.closed_socket",
        )
    )

    assert delivered is False
    assert socket.messages == []


def test_dashboard_connection_manager_removes_dead_socket_after_send_failure():
    socket = DummyWebSocket(fail_send=True)
    manager = DashboardConnectionManager()

    asyncio.run(manager.connect("user-1", socket))
    asyncio.run(
        manager.broadcast_snapshot(
            "user-1",
            {
                "steps": {"value": 1200},
                "last_updated": "2026-05-14T10:00:00+00:00",
            },
        )
    )

    assert asyncio.run(manager.has_connection("user-1")) is False


def test_get_cached_realtime_payload_derives_from_bundle_cache(monkeypatch):
    bundle = {
        "healthScore": {"data": {"score": 82}, "last_updated": "2026-05-14T10:00:00+00:00"},
        "forecast": {"data": {"trend": "stable"}, "last_updated": "2026-05-14T10:00:00+00:00"},
        "preventive": {"data": {"status": "ready"}, "last_updated": "2026-05-14T10:00:00+00:00"},
        "recommendedTests": {"data": [], "last_updated": "2026-05-14T10:00:00+00:00"},
        "googleFit": {"data": {"stats": {"latest_day": {"steps": 4567}}}, "last_updated": "2026-05-14T10:00:00+00:00"},
        "vitals": {
            "heart_rate:24h": {"data": [], "last_updated": "2026-05-14T10:00:00+00:00"},
            "steps:24h": {"data": [], "last_updated": "2026-05-14T10:00:00+00:00"},
        },
        "last_updated": "2026-05-14T10:00:00+00:00",
    }
    set_mock = AsyncMock()
    refresh_mock = AsyncMock()

    async def _get(kind: str, user_id: str):
        if kind == "bundle":
            return bundle
        return None

    monkeypatch.setattr(dashboard_realtime.RealtimeSnapshotCache, "get", _get)
    monkeypatch.setattr(dashboard_realtime.RealtimeSnapshotCache, "get_stale", AsyncMock(return_value=None))
    monkeypatch.setattr(dashboard_realtime.RealtimeSnapshotCache, "set", set_mock)
    monkeypatch.setattr(dashboard_realtime, "ensure_dashboard_snapshot_refresh", refresh_mock)

    payload = asyncio.run(dashboard_realtime.get_cached_realtime_payload("user-1", schedule_refresh=True))

    assert payload["health_score"] == 82
    assert payload["steps"] == 4567
    set_mock.assert_awaited_once()
    refresh_mock.assert_awaited_once()


def test_get_cached_dashboard_bundle_returns_stale_snapshot_and_queues_refresh(monkeypatch):
    stale_bundle = {
        "healthScore": {"data": {"score": 79}, "last_updated": "2026-05-14T10:00:00+00:00"},
        "last_updated": "2026-05-14T10:00:00+00:00",
    }
    refresh_mock = AsyncMock()

    async def _cached_bundle(_user_id: str):
        return stale_bundle, True

    monkeypatch.setattr(dashboard_realtime, "_cached_bundle_or_stale", _cached_bundle)
    monkeypatch.setattr(dashboard_realtime, "ensure_dashboard_snapshot_refresh", refresh_mock)

    payload = asyncio.run(
        dashboard_realtime.get_cached_dashboard_bundle(
            db=SimpleNamespace(),
            current_user=SimpleNamespace(id="user-1"),
            allow_sync_seed=False,
        )
    )

    assert payload["healthScore"]["data"]["score"] == 79
    refresh_mock.assert_awaited_once()
