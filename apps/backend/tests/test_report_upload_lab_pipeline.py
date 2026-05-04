from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import BackgroundTasks

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from models import ReportStatusEnum
from integrations.ocr_service import OCRLine, OCRPage, OCRResult, OCRWord
from services import lab_pipeline_service
from services.report_service import ReportService


class FakeUploadFile:
    def __init__(self, filename: str, content_type: str, content: bytes):
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self) -> bytes:
        return self._content


def test_upload_and_summarize_returns_uploaded_report_and_queues_processing():
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4())
    report_id = uuid4()
    created_at = datetime(2026, 4, 30, 10, 0, tzinfo=timezone.utc)
    file = FakeUploadFile("cbc-report.pdf", "application/pdf", b"%PDF-1.4 fake")
    background_tasks = BackgroundTasks()
    added: dict[str, object] = {}

    def add_side_effect(report):
        report.id = report_id
        report.created_at = created_at
        report.updated_at = created_at
        added["report"] = report

    db.add.side_effect = add_side_effect

    with patch.object(
        ReportService,
        "_persist_file",
        return_value=("reports/user/cbc-report.pdf", "https://example.test/cbc-report.pdf"),
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
    assert result["status"] == "uploaded"
    assert result["data"]["id"] == str(report_id)
    assert result["data"]["name"] == "cbc-report.pdf"
    assert result["data"]["file_name"] == "cbc-report.pdf"
    assert result["data"]["original_filename"] == "cbc-report.pdf"
    assert result["data"]["stored_filename"] == "cbc-report.pdf"
    assert result["data"]["status"] == ReportStatusEnum.PROCESSING.value
    assert result["data"]["summary"] == [ReportService.PROCESSING_SUMMARY]
    assert result["data"]["summary_view"]["key_findings"] == [ReportService.PROCESSING_SUMMARY]
    assert added["report"].original_filename == "cbc-report.pdf"
    assert added["report"].stored_filename == "cbc-report.pdf"
    assert added["report"].summary_data["upload_metadata"]["original_filename"] == "cbc-report.pdf"
    assert len(background_tasks.tasks) == 1
    task = background_tasks.tasks[0]
    assert task.func == ReportService.process_uploaded_report
    assert task.args == (str(report_id), "cbc-report.pdf", "application/pdf", b"%PDF-1.4 fake")


def test_serialize_report_prefers_original_filename_over_uuid_storage_name():
    report_id = uuid4()
    created_at = datetime(2026, 4, 30, 10, 0, tzinfo=timezone.utc)
    report = SimpleNamespace(
        id=report_id,
        report_type=SimpleNamespace(value="BLOOD_TEST"),
        status=ReportStatusEnum.COMPLETED,
        file_url="https://example.test/storage/123e4567-e89b-12d3-a456-426614174000-blood_test_may.pdf",
        original_filename="blood_test_may.pdf",
        stored_filename="123e4567-e89b-12d3-a456-426614174000-blood_test_may.pdf",
        storage_path="reports/user/123e4567-e89b-12d3-a456-426614174000-blood_test_may.pdf",
        summary_data={"summary": ["Ready"], "upload_metadata": {"file_size": 128}},
        parsed_text="",
        created_at=created_at,
        updated_at=created_at,
    )

    serialized = ReportService._serialize_report(report)

    assert serialized["name"] == "blood_test_may.pdf"
    assert serialized["file_name"] == "blood_test_may.pdf"
    assert serialized["original_filename"] == "blood_test_may.pdf"
    assert serialized["stored_filename"] == "123e4567-e89b-12d3-a456-426614174000-blood_test_may.pdf"


def test_serialize_report_returns_saved_summary_payload_for_detail_view():
    report_id = uuid4()
    created_at = datetime(2026, 4, 30, 10, 0, tzinfo=timezone.utc)
    report = SimpleNamespace(
        id=report_id,
        report_type=SimpleNamespace(value="BLOOD_TEST"),
        status=ReportStatusEnum.COMPLETED,
        file_url="https://example.test/storage/cbc.pdf",
        original_filename="cbc.pdf",
        stored_filename="cbc.pdf",
        storage_path="reports/user/cbc.pdf",
        summary_data={
            "summary": "Parsed 2 key measurements from the uploaded report.",
            "risks": ["No acute high-risk pattern was detected."],
            "risk_level": "Low",
            "recommendations": ["Continue routine follow-up."],
            "abnormal_values": [{"name": "Hemoglobin", "value": "13.8", "status": "Optimal"}],
            "summary_source": "prediction-service",
            "upload_metadata": {"file_size": 128},
        },
        parsed_text="Hemoglobin 13.8 g/dL",
        created_at=created_at,
        updated_at=created_at,
    )

    serialized = ReportService._serialize_report(report)

    assert serialized["summary"] == ["Parsed 2 key measurements from the uploaded report."]
    assert serialized["summary_view"]["summary"] == "Parsed 2 key measurements from the uploaded report."
    assert serialized["summary_view"]["key_findings"] == ["Parsed 2 key measurements from the uploaded report."]
    assert serialized["risks"] == ["No acute high-risk pattern was detected."]
    assert serialized["risk_level"] == "Low"
    assert serialized["recommendations"] == ["Continue routine follow-up."]
    assert serialized["abnormal_values"][0]["name"] == "Hemoglobin"


def test_delete_report_removes_storage_before_db_record():
    report_id = uuid4()
    user_id = uuid4()
    db = MagicMock()
    current_user = SimpleNamespace(id=user_id)
    report = SimpleNamespace(
        id=report_id,
        user_id=user_id,
        is_deleted=False,
        storage_path="reports/user/cbc.pdf",
        storage_bucket=None,
        file_url="https://example.test/storage/cbc.pdf",
        summary_data={},
    )
    query = MagicMock()
    query.filter.return_value.first.return_value = report
    db.query.return_value = query

    with patch.object(ReportService, "_delete_stored_file") as delete_stored_file:
        result = ReportService.delete_report(db, current_user, str(report_id))

    assert result["success"] is True
    assert result["data"]["id"] == str(report_id)
    delete_stored_file.assert_called_once_with(report)
    db.delete.assert_called_once_with(report)
    db.commit.assert_called_once()


def test_delete_stored_file_removes_existing_local_file():
    report = SimpleNamespace(
        storage_path="uploads/reports/report.pdf",
        storage_bucket=None,
        file_url="",
        summary_data={},
    )

    with patch.object(Path, "is_file", return_value=True), patch.object(Path, "unlink") as unlink_file:
        ReportService._delete_stored_file(report)

    unlink_file.assert_called_once()


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


def test_analyze_report_always_runs_ocr_for_pdf_even_when_pdf_text_exists():
    word = OCRWord(
        text="Hemoglobin",
        bbox={"x_min": 10, "y_min": 20, "x_max": 90, "y_max": 34},
        confidence=0.91,
        page_number=1,
    )
    ocr_result = OCRResult(
        text="Hemoglobin 14.1 g/dL",
        provider="tesseract",
        source_type="ocr_tesseract",
        confidence=0.88,
        page_count=1,
        pages=[
            OCRPage(
                page_number=1,
                text="Hemoglobin 14.1 g/dL",
                confidence=0.88,
                words=[word],
                lines=[OCRLine(text="Hemoglobin 14.1 g/dL", words=[word], confidence=0.88, page_number=1)],
            )
        ],
    )

    with patch.object(
        ReportService,
        "_extract_pdf_pages",
        return_value=[{"page_number": 1, "text": "Hemoglobin 13.9 g/dL", "source_type": "PDF", "confidence": 1.0}],
    ), patch("services.report_service.OCRService") as ocr_service:
        ocr_service.return_value.extract_text.return_value = ocr_result

        analysis = asyncio.run(
            ReportService._analyze_report("cbc-report.pdf", "application/pdf", b"%PDF-1.4 fake")
        )

    ocr_service.return_value.extract_text.assert_called_once()
    assert analysis["text_source"] == "OCR"
    assert analysis["ocr_provider"] == "tesseract"
    assert analysis["text_pages"][0]["source_type"] == "OCR"
    assert analysis["text_pages"][0]["words"][0]["bbox"]["x_min"] == 10


def test_extract_lab_values_adds_confidence_and_source_span_for_scanned_text():
    text = """
    Complete Blood Count
    Haemoglobin Result 13.8 g/dL Reference 13.5 - 17.5
    Total Leukocyte Count 6.4 10^3/uL 4.0 - 11.0
    Platelet Count 210 10^3/uL
    """

    raw = lab_pipeline_service.extract_lab_values(
        text,
        source_type="ocr_tesseract",
        source_confidence=0.82,
    )
    normalized = lab_pipeline_service.normalize_lab_values(raw)
    by_name = {item["name"]: item for item in normalized}

    assert by_name["Hemoglobin"]["value"] == 13.8
    assert by_name["Hemoglobin"]["confidence_score"] > 0.7
    assert by_name["Hemoglobin"]["source_type"] == "OCR"
    assert by_name["Hemoglobin"]["source_text"]
    assert by_name["Hemoglobin"]["page_number"] == 1
    assert "Haemoglobin" in by_name["Hemoglobin"]["source_span"]
    assert by_name["WBC"]["value"] == 6.4
    assert by_name["Platelets"]["value"] == 210.0


def test_extract_lab_values_uses_layout_words_and_attaches_bbox():
    words = [
        {"text": "Haemoglobin", "bbox": {"x_min": 10, "y_min": 20, "x_max": 95, "y_max": 34}, "confidence": 0.93},
        {"text": "13.8", "bbox": {"x_min": 210, "y_min": 20, "x_max": 245, "y_max": 34}, "confidence": 0.95},
        {"text": "g/dL", "bbox": {"x_min": 260, "y_min": 20, "x_max": 295, "y_max": 34}, "confidence": 0.92},
        {"text": "13.5", "bbox": {"x_min": 360, "y_min": 20, "x_max": 395, "y_max": 34}, "confidence": 0.91},
        {"text": "-", "bbox": {"x_min": 401, "y_min": 20, "x_max": 408, "y_max": 34}, "confidence": 0.9},
        {"text": "17.5", "bbox": {"x_min": 415, "y_min": 20, "x_max": 450, "y_max": 34}, "confidence": 0.91},
        {"text": "WBC", "bbox": {"x_min": 10, "y_min": 48, "x_max": 45, "y_max": 62}, "confidence": 0.88},
        {"text": "6.4", "bbox": {"x_min": 210, "y_min": 48, "x_max": 238, "y_max": 62}, "confidence": 0.9},
        {"text": "10^3/uL", "bbox": {"x_min": 260, "y_min": 48, "x_max": 325, "y_max": 62}, "confidence": 0.86},
    ]

    raw = lab_pipeline_service.extract_lab_values(
        "Haemoglobin 13.8 g/dL 13.5 - 17.5\nWBC 6.4 10^3/uL",
        source_type="ocr_google_vision",
        source_confidence=0.9,
        page_metadata=[
            {
                "page_number": 1,
                "text": "Haemoglobin 13.8 g/dL 13.5 - 17.5\nWBC 6.4 10^3/uL",
                "source_type": "OCR",
                "confidence": 0.9,
                "words": words,
            }
        ],
    )
    normalized = lab_pipeline_service.normalize_lab_values(raw)
    by_name = {item["name"]: item for item in normalized}

    assert by_name["Hemoglobin"]["value"] == 13.8
    assert by_name["Hemoglobin"]["extraction_method"] == "layout_row"
    assert by_name["Hemoglobin"]["bbox"]["x_min"] == 210
    assert by_name["Hemoglobin"]["confidence_score"] >= 0.85
    assert by_name["WBC"]["bbox"]["x_min"] == 210


def test_run_lab_pipeline_passes_ocr_provenance_from_report_summary():
    report_id = uuid4()
    user_id = uuid4()
    db = MagicMock()
    report = SimpleNamespace(
        id=report_id,
        user_id=user_id,
        parsed_text="Hemoglobin 13.8 g/dL",
        summary_data={"text_source": "ocr_google_vision", "ocr_confidence": 0.91},
        is_deleted=False,
    )
    query = MagicMock()
    query.filter.return_value.first.return_value = report
    db.query.return_value = query

    with patch.object(lab_pipeline_service, "SessionLocal", return_value=db), patch.object(
        lab_pipeline_service,
        "_run_pipeline",
        return_value=[],
    ) as run_pipeline:
        lab_pipeline_service.run_lab_pipeline(str(report_id))

    run_pipeline.assert_called_once_with(
        "Hemoglobin 13.8 g/dL",
        user_id,
        report_id,
        db,
        source_type="OCR",
        source_confidence=0.91,
    )
