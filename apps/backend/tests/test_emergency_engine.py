from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import sys
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.emergency_engine import emergency_engine


def _signals(**updates):
    payload = {
        "heart_rate": {"value": None, "at_rest": None},
        "activity": {"sudden_drop": False, "drop_ratio": None},
        "sleep": {"latest_minutes": None, "anomaly": False},
        "ml": {"risk_score": None},
        "symptoms": {"items": [], "red_flags": [], "has_chest_pain": False, "has_fainting": False},
        "labs": {"abnormal": [], "critical_count": 0},
        "missing": [],
    }
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(payload.get(key), dict):
            payload[key].update(value)
        else:
            payload[key] = value
    return payload


def test_detect_emergency_sends_alert_for_high_resting_heart_rate():
    db = MagicMock()
    user_id = uuid4()

    with patch.object(emergency_engine, "_load_user", return_value=SimpleNamespace(id=user_id)), patch.object(
        emergency_engine,
        "_collect_signals",
        return_value=_signals(heart_rate={"value": 132, "at_rest": True}),
    ), patch.object(
        emergency_engine,
        "_recent_critical_alert",
        return_value=None,
    ), patch.object(
        emergency_engine.notification_service,
        "send_alert",
        return_value={"success": True, "data": {"channels": ["push", "email", "dashboard"]}},
    ) as send_alert:
        result = emergency_engine.detect_emergency(user_id, db=db)

    assert result["data"]["emergency"] is True
    assert result["data"]["alert"]["level"] == "CRITICAL"
    assert result["data"]["alert"]["event"] == "Possible cardiac stress"
    assert result["data"]["alert_sent"] is True
    send_alert.assert_called_once()


def test_detect_emergency_sends_alert_for_high_ml_risk():
    db = MagicMock()
    user_id = uuid4()

    with patch.object(emergency_engine, "_load_user", return_value=SimpleNamespace(id=user_id)), patch.object(
        emergency_engine,
        "_collect_signals",
        return_value=_signals(ml={"risk_score": 0.91}),
    ), patch.object(
        emergency_engine,
        "_recent_critical_alert",
        return_value=None,
    ), patch.object(
        emergency_engine.notification_service,
        "send_alert",
        return_value={"success": True},
    ) as send_alert:
        result = emergency_engine.detect_emergency(user_id, db=db)

    assert result["data"]["emergency"] is True
    assert "ML risk > 0.85" in result["data"]["triggers"]
    send_alert.assert_called_once()


def test_detect_emergency_rate_limits_duplicate_critical_alerts():
    db = MagicMock()
    user_id = uuid4()
    recent = SimpleNamespace(id=uuid4(), created_at=datetime.now(timezone.utc))

    with patch.object(emergency_engine, "_load_user", return_value=SimpleNamespace(id=user_id)), patch.object(
        emergency_engine,
        "_collect_signals",
        return_value=_signals(symptoms={"items": ["chest pain"], "has_chest_pain": True, "red_flags": ["chest pain"]}),
    ), patch.object(
        emergency_engine,
        "_recent_critical_alert",
        return_value=recent,
    ), patch.object(emergency_engine.notification_service, "send_alert") as send_alert:
        result = emergency_engine.detect_emergency(user_id, db=db)

    assert result["data"]["emergency"] is True
    assert result["data"]["rate_limited"] is True
    assert result["data"]["alert_sent"] is False
    send_alert.assert_not_called()
