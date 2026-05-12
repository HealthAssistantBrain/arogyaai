from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
import os
import sys
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
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

from core.serialization.json_safe import make_json_safe
from core.serialization.safe_response import SafeJSONResponse, safe_json_dumps, websocket_send_json_safe
from core.config import settings
from services import dashboard_realtime
from services.dashboard_realtime import DashboardConnectionManager, build_realtime_payload


class RiskLevel(Enum):
    HIGH = "high"


class DummyWebSocket:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.accepted = False
        self.closed = False
        self.close_code = None
        self.close_reason = None

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, message: str) -> None:
        self.messages.append(message)

    async def close(self, code: int | None = None, reason: str | None = None) -> None:
        self.closed = True
        self.close_code = code
        self.close_reason = reason


def test_make_json_safe_normalizes_nested_payloads():
    stamp = datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc)
    payload = {
        "amount": Decimal("42.5"),
        "uuid": uuid4(),
        "timestamp": stamp,
        "day": date(2026, 5, 11),
        "level": RiskLevel.HIGH,
        "items": ({1, 2}, ("nested", Decimal("2.5"))),
    }

    safe = make_json_safe(payload)

    assert safe["amount"] == 42.5
    assert isinstance(safe["uuid"], str)
    assert safe["timestamp"] == stamp.isoformat()
    assert safe["day"] == "2026-05-11"
    assert safe["level"] == "high"
    assert sorted(safe["items"][0]) == [1, 2]
    assert safe["items"][1] == ["nested", 2.5]


def test_make_json_safe_traces_nested_paths_in_debug_mode(monkeypatch, caplog):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    caplog.set_level(logging.DEBUG)

    payload = {
        "healthScore": {
            "data": {
                "drivers": [
                    {
                        "weight": Decimal("0.12"),
                        "confidence": np.float32(0.91),
                    }
                ]
            }
        }
    }

    safe = make_json_safe(payload)

    assert safe["healthScore"]["data"]["drivers"][0]["weight"] == 0.12
    assert safe["healthScore"]["data"]["drivers"][0]["confidence"] == pytest.approx(0.91)
    assert "[SERIALIZATION TRACE] field=weight type=Decimal path=$.healthScore.data.drivers[0].weight" in caplog.text
    assert "[SERIALIZATION TRACE] field=confidence type=float32 path=$.healthScore.data.drivers[0].confidence" in caplog.text


def test_make_json_safe_normalizes_numpy_scalars_and_arrays():
    payload = {
        "float32": np.float32(91.25),
        "float64": np.float64(88.5),
        "int64": np.int64(7),
        "vector": np.array([np.float32(1.5), np.int64(2)]),
    }

    safe = make_json_safe(payload)

    assert safe == {
        "float32": 91.25,
        "float64": 88.5,
        "int64": 7,
        "vector": [1.5, 2],
    }


def test_safe_json_response_serializes_decimal_and_datetime_payloads():
    stamp = datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc)
    response = SafeJSONResponse(
        content={
            "score": Decimal("84.2"),
            "generated_at": stamp,
        }
    )

    body = json.loads(response.body)

    assert body == {
        "score": 84.2,
        "generated_at": stamp.isoformat(),
    }


def test_websocket_send_json_safe_serializes_payload():
    socket = DummyWebSocket()
    payload = {
        "type": "dashboard.update",
        "score": Decimal("73.4"),
        "trend": np.float64(0.82),
        "generated_at": datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
    }

    asyncio.run(websocket_send_json_safe(socket, payload))

    assert len(socket.messages) == 1
    delivered = json.loads(socket.messages[0])
    assert delivered == {
        "type": "dashboard.update",
        "score": 73.4,
        "trend": 0.82,
        "generated_at": "2026-05-11T12:00:00+00:00",
    }


def test_safe_json_dumps_handles_scoring_payloads():
    payload = {
        "healthScore": {
            "data": {
                "score": Decimal("79.9"),
                "confidence": np.float32(0.93),
                "drivers": [
                    {
                        "feature": "resting_hr",
                        "weight": np.float64(0.12),
                    }
                ],
            },
            "last_updated": datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
        }
    }

    serialized = json.loads(safe_json_dumps(payload))

    assert serialized["healthScore"]["data"]["score"] == 79.9
    assert serialized["healthScore"]["data"]["confidence"] == pytest.approx(0.93)
    assert serialized["healthScore"]["data"]["drivers"] == [
        {
            "feature": "resting_hr",
            "weight": 0.12,
        }
    ]
    assert serialized["healthScore"]["last_updated"] == "2026-05-11T12:00:00+00:00"


def test_safe_json_dumps_degrades_when_normalizer_raises(monkeypatch):
    monkeypatch.setattr("core.serialization.safe_response.make_json_safe", lambda _value: (_ for _ in ()).throw(RuntimeError("boom")))

    serialized = json.loads(
        safe_json_dumps(
            {
                "type": "dashboard.update",
                "user_id": "user-123",
                "data": {"score": Decimal("88.2")},
            },
            channel="dashboard.broadcast",
        )
    )

    assert serialized["type"] == "dashboard.update"
    assert serialized["user_id"] == "user-123"
    assert serialized["data"]["status"] == "degraded"
    assert serialized["data"]["error"] == "payload_sanitized"
    assert serialized["meta"]["degraded"] is True


def test_dashboard_connection_manager_broadcast_serializes_payloads():
    socket = DummyWebSocket()
    manager = DashboardConnectionManager()
    asyncio.run(manager.connect("user-1", socket))

    asyncio.run(
        manager.broadcast(
            "user-1",
            {
                "type": "dashboard.update",
                "user_id": "user-1",
                "data": {
                    "score": Decimal("81.4"),
                    "confidence": np.float64(0.94),
                    "generated_at": datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
                    "request_id": uuid4(),
                },
            },
        )
    )

    assert len(socket.messages) == 1
    delivered = json.loads(socket.messages[0])
    assert delivered["type"] == "dashboard.update"
    assert delivered["data"]["score"] == 81.4
    assert delivered["data"]["confidence"] == 0.94
    assert delivered["data"]["generated_at"] == "2026-05-11T12:00:00+00:00"
    assert isinstance(delivered["data"]["request_id"], str)


def test_build_realtime_payload_normalizes_dashboard_snapshot(monkeypatch):
    async def _run_user_slice(_user_id, fetcher, *, fallback_data=None):
        result = fetcher(SimpleNamespace(), SimpleNamespace(id="user-1"))
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def _health_score(_user, _db):
        return {
            "data": {
                "score": Decimal("84.6"),
                "confidence": np.float32(0.97),
                "generated_at": datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
            },
            "last_updated": datetime(2026, 5, 11, 12, 0, tzinfo=timezone.utc),
        }

    async def _forecast(_user, _db):
        return {
            "data": {
                "trend": np.float64(1.5),
                "risk_id": uuid4(),
            },
            "last_updated": datetime(2026, 5, 11, 12, 5, tzinfo=timezone.utc),
        }

    async def _recommended_tests(_user, _db):
        return {
            "data": [
                {
                    "priority": Decimal("1.0"),
                }
            ],
            "last_updated": datetime(2026, 5, 11, 12, 10, tzinfo=timezone.utc),
        }

    monkeypatch.setattr(dashboard_realtime.dashboard_svc, "get_health_score", _health_score)
    monkeypatch.setattr(dashboard_realtime.dashboard_svc, "get_health_forecast", _forecast)
    monkeypatch.setattr(
        dashboard_realtime.dashboard_svc,
        "get_preventive_intelligence",
        lambda _user, _db: {
            "data": {"status": "ready"},
            "last_updated": datetime(2026, 5, 11, 12, 7, tzinfo=timezone.utc),
        },
    )
    monkeypatch.setattr(dashboard_realtime.dashboard_svc, "get_recommended_tests", _recommended_tests)
    monkeypatch.setattr(
        dashboard_realtime,
        "_serialize_vitals_slice",
        lambda _db, _user, vital_type, _range="24h": {
            "type": vital_type,
            "data": [
                {
                    "timestamp": datetime(2026, 5, 11, 12, 15, tzinfo=timezone.utc),
                    "value": Decimal("72.2"),
                }
            ],
            "last_updated": datetime(2026, 5, 11, 12, 15, tzinfo=timezone.utc),
        },
    )
    monkeypatch.setattr(
        dashboard_realtime.GoogleFitService,
        "get_status",
        lambda _db, _user: {
            "last_synced_at": datetime(2026, 5, 11, 12, 20, tzinfo=timezone.utc),
            "stats": {
                "latest_day": {
                    "steps": Decimal("4567"),
                }
            },
        },
    )
    monkeypatch.setattr(dashboard_realtime, "_run_user_slice", _run_user_slice)

    payload = asyncio.run(build_realtime_payload(db=None, current_user=SimpleNamespace(id="user-1")))

    assert payload["healthScore"]["data"]["score"] == 84.6
    assert payload["healthScore"]["data"]["confidence"] == pytest.approx(0.97)
    assert payload["forecast"]["trend"] == 1.5
    assert isinstance(payload["googleFit"]["data"]["last_synced_at"], str)
    assert payload["recommended_tests"][0]["priority"] == 1.0
    assert payload["heart_rate"]["data"][0]["value"] == 72.2
    assert payload["last_updated"] == "2026-05-11T12:20:00+00:00"


def test_streaming_update_publisher_falls_back_to_degraded_broadcast(monkeypatch):
    captured: list[dict[str, object]] = []

    async def _raise(_user_id: str) -> None:
        raise RuntimeError("snapshot failed")

    async def _capture(user_id: str, payload: dict[str, object]) -> None:
        captured.append({"user_id": user_id, "payload": payload})

    monkeypatch.setattr("ai.scoring.realtime.streaming_updates._broadcast_current_snapshot", _raise)
    monkeypatch.setattr("ai.scoring.realtime.streaming_updates.dashboard_connection_manager.broadcast", _capture)

    from ai.scoring.realtime.streaming_updates import StreamingUpdatePublisher

    asyncio.run(StreamingUpdatePublisher.publish_user_refresh("user-9"))

    assert len(captured) == 1
    assert captured[0]["user_id"] == "user-9"
    payload = captured[0]["payload"]
    assert isinstance(payload, dict)
    assert payload["type"] == "dashboard.update"
    assert payload["data"]["status"] == "degraded"
    assert payload["meta"]["degraded"] is True
