from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import BackgroundTasks

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from models import ReportStatusEnum
from services import lab_pipeline_service
from services.report_service import ReportService


class FakeUploadFile:
    def __init__(self, filename: str, content_type: str, content: bytes):
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self) -> bytes:
        return self._content


def test_upload_and_summarize_queues_background_lab_pipeline():
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4())
    report_id = uuid4()
    created_at = datetime(2026, 4, 30, 10, 0, tzinfo=timezone.utc)
    file = FakeUploadFile("cbc-report.pdf", "application/pdf", b"%PDF-1.4 fake")
    background_tasks = BackgroundTasks()
    lab_runner = MagicMock()
    added: dict[str, object] = {}

    def add_side_effect(report):
        report.id = report_id
        report.created_at = created_at
        report.updated_at = created_at
        added["report"] = report

    def persist_side_effect(db_session, persisted_report_id, parsed_text, summary_data):
        report = added["report"]
        report.parsed_text = parsed_text
        report.summary_data = summary_data
        report.status = ReportStatusEnum.COMPLETED
        assert persisted_report_id == str(report_id)
        assert parsed_text == "Hemoglobin 13.8 WBC 6.4"

    db.add.side_effect = add_side_effect

    analysis = {
        "title": "Cbc Report",
        "summary": ["Report text extracted successfully."],
        "full_text": "Hemoglobin 13.8 WBC 6.4",
        "ocr_text": "Hemoglobin 13.8 WBC 6.4",
        "markers": [{"name": "Hemoglobin", "value": "13.8", "unit": "g/dL", "flag": "captured"}],
        "source": "local-pdf",
    }

    with patch.object(ReportService, "_persist_file", return_value=("reports/user/cbc-report.pdf", "https://example.test/cbc-report.pdf")), patch.object(
        ReportService,
        "_analyze_report",
        AsyncMock(return_value=analysis),
    ), patch.object(
        ReportService,
        "persist_report",
        side_effect=persist_side_effect,
    ), patch.object(
        ReportService,
        "_load_lab_pipeline_runner",
        return_value=lab_runner,
    ):
        result = asyncio.run(
            ReportService.upload_and_summarize(
                db,
                current_user,
                file,
                "BLOOD_TEST",
                background_tasks=background_tasks,
            )
        )

    assert result["success"] is True
    assert result["data"]["id"] == str(report_id)
    assert len(background_tasks.tasks) == 1
    task = background_tasks.tasks[0]
    assert task.func is lab_runner
    assert task.args == (str(report_id),)


def test_run_lab_pipeline_can_resolve_report_from_report_id():
    report_id = uuid4()
    user_id = uuid4()
    db = MagicMock()
    report = SimpleNamespace(
        id=report_id,
        user_id=user_id,
        parsed_text="Hemoglobin 13.8 WBC 6.4",
        summary_data=None,
        is_deleted=False,
    )
    query = MagicMock()
    query.filter.return_value.first.return_value = report
    db.query.return_value = query

    with patch.object(lab_pipeline_service, "SessionLocal", return_value=db), patch.object(
        lab_pipeline_service,
        "_run_pipeline",
        return_value=[{"name": "Hemoglobin", "value": 13.8}],
    ) as run_pipeline:
        result = lab_pipeline_service.run_lab_pipeline(str(report_id))

    assert result == [{"name": "Hemoglobin", "value": 13.8}]
    run_pipeline.assert_called_once_with("Hemoglobin 13.8 WBC 6.4", user_id, report_id, db)
    db.close.assert_called_once()
