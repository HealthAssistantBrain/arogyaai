from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from models import SeverityEnum
from services import alert_service


def test_generate_health_alerts_persists_threshold_breaches():
    db = MagicMock()
    user_id = uuid4()
    captured_alerts = []

    heart_rate_row = SimpleNamespace(value=108.0, unit="bpm")
    sleep_row = SimpleNamespace(value=4.5, unit="hours")
    risk_row = SimpleNamespace(overall_score=0.81)

    db.add.side_effect = captured_alerts.append

    with patch.object(alert_service, "_load_user", return_value=SimpleNamespace(id=user_id)), patch.object(
        alert_service,
        "_latest_user_vital",
        side_effect=[heart_rate_row, sleep_row],
    ), patch.object(
        alert_service,
        "_latest_risk_score",
        return_value=risk_row,
    ), patch.object(
        alert_service,
        "_find_recent_duplicate_alert",
        return_value=None,
    ), patch.object(
        alert_service,
        "_list_active_alert_models",
        side_effect=lambda *args, **kwargs: list(captured_alerts),
    ):
        alerts = alert_service.generate_health_alerts(user_id, db)

    assert len(captured_alerts) == 3
    assert {item.title for item in captured_alerts} == {
        "High heart rate detected",
        "Low sleep duration detected",
        "Elevated health risk score detected",
    }
    assert {item.severity for item in captured_alerts} == {
        SeverityEnum.CRITICAL,
        SeverityEnum.WARNING,
    }
    assert {item["severity_label"] for item in alerts} == {"HIGH", "MEDIUM"}
    db.commit.assert_called_once()


def test_generate_health_alerts_skips_recent_duplicates():
    db = MagicMock()
    user_id = uuid4()

    heart_rate_row = SimpleNamespace(value=112.0, unit="bpm")
    sleep_row = SimpleNamespace(value=280.0, unit="minutes")
    risk_row = SimpleNamespace(overall_score=0.93)

    with patch.object(alert_service, "_load_user", return_value=SimpleNamespace(id=user_id)), patch.object(
        alert_service,
        "_latest_user_vital",
        side_effect=[heart_rate_row, sleep_row],
    ), patch.object(
        alert_service,
        "_latest_risk_score",
        return_value=risk_row,
    ), patch.object(
        alert_service,
        "_find_recent_duplicate_alert",
        return_value=SimpleNamespace(id=uuid4()),
    ), patch.object(
        alert_service,
        "_list_active_alert_models",
        return_value=[],
    ):
        alerts = alert_service.generate_health_alerts(user_id, db)

    assert alerts == []
    db.add.assert_not_called()
    db.commit.assert_not_called()
