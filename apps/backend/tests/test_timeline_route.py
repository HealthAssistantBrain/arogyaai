from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from models.clinical_history import ClinicalHistory
from models.lab_result import LabResult
from models.notification import Notification
from models.report import Report
from models.user_vital import UserVital
from routes.timeline import get_timeline
from services.clinical_history_service import ClinicalHistoryService


class FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)


class FakeSession:
    def __init__(self, rows_by_model):
        self._rows_by_model = rows_by_model

    def query(self, model):
        return FakeQuery(self._rows_by_model.get(model, []))


def test_timeline_prefers_event_date_and_sorts_chronologically():
    user_id = uuid4()
    report_with_history_date_id = uuid4()
    report_without_history_date_id = uuid4()
    alert_id = uuid4()
    history_id = uuid4()

    report_with_history_date = SimpleNamespace(
        id=report_with_history_date_id,
        user_id=user_id,
        is_deleted=False,
        summary_data={
            "title": "Chest X-Ray Review",
            "summary": ["Historical imaging uploaded.", "Mild chronic changes noted."],
            "upload_metadata": {"date_of_report": "2023-05-03"},
        },
        report_type=SimpleNamespace(value="XRAY"),
        status=SimpleNamespace(value="COMPLETED"),
        created_at=datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc),
    )
    report_without_history_date = SimpleNamespace(
        id=report_without_history_date_id,
        user_id=user_id,
        is_deleted=False,
        summary_data={
            "title": "CBC Panel",
            "summary": ["Routine blood panel uploaded."],
        },
        report_type=SimpleNamespace(value="BLOOD_TEST"),
        status=SimpleNamespace(value="COMPLETED"),
        created_at=datetime(2025, 1, 20, 9, 30, tzinfo=timezone.utc),
    )
    alert = SimpleNamespace(
        id=alert_id,
        user_id=user_id,
        title="Elevated blood pressure",
        description="Systolic reading remained above threshold.",
        created_at=datetime(2024, 7, 1, 8, 0, tzinfo=timezone.utc),
        severity=SimpleNamespace(value="high"),
        notification_type=SimpleNamespace(value="HEALTH_ALERT"),
    )
    history = SimpleNamespace(id=history_id, user_id=user_id)

    db = FakeSession(
        {
            UserVital: [],
            LabResult: [],
            Notification: [alert],
            Report: [report_with_history_date, report_without_history_date],
            ClinicalHistory: [history],
        }
    )

    history_event = {
        "id": f"clinical_history_{history_id}",
        "type": "Clinical History",
        "source": "patient intake",
        "category": "symptom",
        "title": "Chest tightness",
        "description": "Structured symptom history added.",
        "timestamp": "2026-01-02T10:15:00+00:00",
        "event_date": "2026-01-02T10:15:00+00:00",
        "metrics": [{"label": "Severity", "value": "6/10"}],
    }

    with patch.object(ClinicalHistoryService, "build_timeline_event", return_value=history_event):
        payload = get_timeline(current_user=SimpleNamespace(id=user_id), db=db)

    events = payload["data"]

    assert [event["id"] for event in events] == [
        f"report_{report_with_history_date_id}",
        f"alert_{alert_id}",
        f"report_{report_without_history_date_id}",
        f"clinical_history_{history_id}",
    ]
    assert events[0]["event_date"] == "2023-05-03"
    assert events[1]["event_date"] == "2024-07-01T08:00:00+00:00"
    assert events[2]["event_date"] == "2025-01-20T09:30:00+00:00"
    assert payload["last_updated"] == "2026-01-02T10:15:00+00:00"


def test_build_timeline_event_includes_event_date():
    created_at = datetime(2026, 2, 14, 15, 45, tzinfo=timezone.utc)
    record = SimpleNamespace(
        id=uuid4(),
        chief_complaint="Persistent cough",
        associated_symptoms=["Fatigue"],
        negative_symptoms=["fever"],
        severity=4,
        created_at=created_at,
    )

    analysis = {
        "summary": "Symptoms suggest a mild respiratory pattern.",
        "risk_level": "low",
        "priority": "routine",
        "system_flags": {"respiratory": True},
        "possible_conditions": ["Upper respiratory infection"],
        "recommendations": ["Hydrate and monitor symptom progression."],
    }

    event = ClinicalHistoryService.build_timeline_event(record, analysis=analysis)

    assert event["event_date"] == created_at.isoformat()
    assert event["severity"] == "4/10"
    assert event["metadata"]["severity"] == 4
