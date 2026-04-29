from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.audit_service import log_event


def test_log_event_persists_normalized_payload():
    db = MagicMock()
    captured: dict[str, object] = {}
    user_id = uuid4()
    happened_at = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)

    def fake_log(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(**kwargs)

    with patch("services.audit_service.SessionLocal", return_value=db), patch(
        "services.audit_service.Log",
        side_effect=fake_log,
    ):
        log_event(
            str(user_id),
            "prediction_run",
            "/api/v1/prediction/run",
            {
                "when": happened_at,
                "score": Decimal("42.5"),
                "nested": {"user_id": user_id},
            },
        )

    assert captured["user_id"] == user_id
    assert captured["action"] == "prediction_run"
    assert captured["endpoint"] == "/api/v1/prediction/run"
    assert captured["details"] == {
        "when": happened_at.isoformat(),
        "score": 42.5,
        "nested": {"user_id": str(user_id)},
    }
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.close.assert_called_once()


def test_log_event_rolls_back_when_insert_fails():
    db = MagicMock()
    db.add.side_effect = RuntimeError("insert failed")

    with patch("services.audit_service.SessionLocal", return_value=db):
        log_event(None, "login", "/api/v1/auth/login", {"status": "failed"})

    db.rollback.assert_called_once()
    db.close.assert_called_once()
