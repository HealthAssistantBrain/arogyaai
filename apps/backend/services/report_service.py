import asyncio
import json
import logging
import mimetypes
import re
import uuid
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from fastapi import BackgroundTasks, HTTPException, UploadFile, status

try:
    from pypdf import PdfReader
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    PdfReader = None
from sqlalchemy.orm import Session

from core.config import settings
from core.pipeline_logger import log_pipeline
from database.session import SessionLocal
from integrations.ocr_service import OCRInput, OCRResult, OCRService
from integrations.prediction_client import PredictionClient
from integrations.supabase_storage import delete_report as _supabase_delete_report
from integrations.supabase_storage import upload_report as _supabase_upload_report
from models import Report, ReportStatusEnum, ReportTypeEnum, User
from services.notification_service import trigger_notification
from services.timeline_service import create_report_timeline_event

logger = logging.getLogger("uvicorn.error")


class ReportService:
    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
    PROCESSING_SUMMARY = "Report uploaded successfully. Analysis is in progress."

    @classmethod
    async def upload_and_summarize(
        cls,
        db: Session,
        current_user: User,
        file: UploadFile,
        report_type: str,
        date_of_report: str | None = None,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        cls._validate_report_type(report_type)
        normalized_report_date = cls._normalize_report_date(date_of_report)
        original_filename = file.filename or "report"
        extension = Path(original_filename).suffix.lower()
        if extension not in cls.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF, JPG, JPEG, and PNG files are supported.",
            )

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
        if len(file_bytes) > cls.MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is too large. Please upload a report smaller than 10 MB.",
            )

        log_pipeline("report", step="upload_file", status="running", data="pending")
        storage_path, public_url = cls._persist_file(current_user.id, original_filename, file_bytes)
        stored_filename = cls._stored_filename(storage_path, public_url)
        log_pipeline("report", step="upload_file", status="healthy", data="stored")

        report = Report(
            user_id=current_user.id,
            report_type=ReportTypeEnum(report_type),
            file_url=public_url,
            original_filename=original_filename,
            stored_filename=stored_filename,
            storage_path=str(storage_path),
            summary_data={
                "upload_metadata": {
                    "date_of_report": normalized_report_date,
                    "file_name": original_filename,
                    "original_filename": original_filename,
                    "stored_filename": stored_filename,
                    "file_size": len(file_bytes),
                    "storage_path": str(storage_path),
                }
            },
            status=ReportStatusEnum.PROCESSING,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        create_report_timeline_event(db, report)

        cls._schedule_report_processing(
            str(report.id),
            original_filename,
            file.content_type,
            file_bytes,
            background_tasks=background_tasks,
        )

        return {
            "success": True,
            "status": "uploaded",
            "error": None,
            "data": {
                "id": str(report.id),
                "name": original_filename,
                "file_name": original_filename,
                "original_filename": original_filename,
                "stored_filename": stored_filename,
                "file_size": len(file_bytes),
                "report_type": report.report_type.value,
                "file_url": report.file_url,
                "status": report.status.value,
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "updated_at": report.updated_at.isoformat() if report.updated_at else None,
                "storage_path": str(storage_path),
                "date_of_report": normalized_report_date,
                "summary": [cls.PROCESSING_SUMMARY],
                "ocr_text": "",
                "markers": [],
                "summary_source": "background-processing",
                "summary_view": cls._build_processing_summary_view(original_filename),
            },
        }

    @classmethod
    def _schedule_report_processing(
        cls,
        report_id: str,
        filename: str,
        content_type: str | None,
        file_bytes: bytes,
        background_tasks: BackgroundTasks | None = None,
    ) -> None:
        if background_tasks is not None:
            background_tasks.add_task(cls.process_uploaded_report, report_id, filename, content_type, file_bytes)
            return

        try:
            asyncio.create_task(cls.process_uploaded_report(report_id, filename, content_type, file_bytes))
        except RuntimeError:
            asyncio.run(cls.process_uploaded_report(report_id, filename, content_type, file_bytes))

    @classmethod
    async def process_uploaded_report(
        cls,
        report_id: str,
        filename: str,
        content_type: str | None,
        file_bytes: bytes,
    ) -> None:
        db = SessionLocal()
        try:
            report = cls._get_report_by_id(db, report_id)
            if not report:
                logger.warning("Skipping report processing because report %s was not found", report_id)
                return

            log_pipeline("report", step="analyze_report", status="running", data="pending")
            analysis = await cls._analyze_report(filename or "report", content_type, file_bytes)
            cls.persist_report(db, report_id, analysis.get("full_text") or analysis.get("ocr_text", ""), analysis)
            cls._schedule_lab_pipeline(report_id)
            db.refresh(report)
            try:
                await trigger_notification(
                    user_id=str(report.user_id),
                    event_type="health_alert",
                    title="Lab Report Processed",
                    message="Your medical report has been analyzed.",
                    data={
                        "report_id": report_id,
                        "report_type": report.report_type.value,
                        "summary": "Your uploaded report is ready for review in ArogyaAI.",
                        "url": "/lab-results",
                        "severity": "info",
                    },
                )
            except Exception:
                logger.exception("Failed to trigger processed-report notification for report %s", report_id)
            log_pipeline(
                "report",
                step="analyze_report",
                status="healthy",
                data="fetched",
                extra=f"source={analysis.get('source', '?')}",
            )
        except Exception as exc:
            logger.exception("Report background processing failed for report %s", report_id)
            report = cls._get_report_by_id(db, report_id)
            if report:
                existing_summary = report.summary_data if isinstance(report.summary_data, dict) else {}
                report.summary_data = {
                    **existing_summary,
                    "processing_error": str(exc),
                }
                report.status = ReportStatusEnum.FAILED
                db.commit()
            log_pipeline("report", step="analyze_report", status="unhealthy", data="failed")
        finally:
            db.close()

    @classmethod
    def list_reports(
        cls,
        db: Session,
        current_user: User,
        status_filter: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = db.query(Report).filter(
            Report.user_id == current_user.id,
            Report.is_deleted == False,
        )

        if status_filter:
            try:
                query = query.filter(Report.status == ReportStatusEnum(status_filter.upper()))
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report status.") from exc

        rows = (
            query.order_by(Report.created_at.desc())
            .offset(max(offset, 0))
            .limit(max(limit, 1))
            .all()
        )

        return [cls._serialize_report(report) for report in rows]

    @classmethod
    def get_report(
        cls,
        db: Session,
        current_user: User,
        report_id: str,
    ) -> dict[str, Any]:
        try:
            report_uuid = uuid.UUID(report_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report id.") from exc

        report = (
            db.query(Report)
            .filter(
                Report.id == report_uuid,
                Report.user_id == current_user.id,
                Report.is_deleted == False,
            )
            .first()
        )

        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

        return cls._serialize_report(report)

    @classmethod
    def get_report_status(
        cls,
        db: Session,
        current_user: User,
        report_id: str,
    ) -> dict[str, Any]:
        report = cls._get_user_report(db, current_user, report_id)
        serialized = cls._serialize_report(report)

        return {
            "success": True,
            "status": serialized["status"],
            "error": serialized.get("summary_data", {}).get("processing_error"),
            "data": {
                "id": serialized["id"],
                "status": serialized["status"],
                "updated_at": serialized["updated_at"],
                "report": serialized,
            },
        }

    @classmethod
    def delete_report(
        cls,
        db: Session,
        current_user: User,
        report_id: str,
    ) -> dict[str, Any]:
        report = cls._get_user_report(db, current_user, report_id)
        deleted_id = str(report.id)

        cls._delete_stored_file(report)
        db.delete(report)
        db.commit()

        return {
            "success": True,
            "message": "Report deleted successfully.",
            "data": {"id": deleted_id},
        }

    @classmethod
    def persist_report(cls, db: Session, report_id: str, parsed_text: str, summary_data: dict[str, Any]) -> Report | None:
        """
        Updates an existing report with the extracted text and AI-generated summary data.
        """
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return None

        existing_summary = report.summary_data if isinstance(report.summary_data, dict) else {}
        merged_summary = dict(existing_summary)
        merged_summary.update(summary_data or {})
        existing_upload_metadata = existing_summary.get("upload_metadata") if isinstance(existing_summary.get("upload_metadata"), dict) else {}
        next_upload_metadata = summary_data.get("upload_metadata") if isinstance(summary_data.get("upload_metadata"), dict) else {}
        if existing_upload_metadata or next_upload_metadata:
            merged_summary["upload_metadata"] = {
                **existing_upload_metadata,
                **next_upload_metadata,
            }

        if not cls._summary_lines(merged_summary.get("summary") or merged_summary.get("patient_summary")):
            merged_summary["summary"] = [cls.PROCESSING_SUMMARY]
            merged_summary["patient_summary"] = cls.PROCESSING_SUMMARY

        report.parsed_text = parsed_text
        report.summary_data = merged_summary
        report.status = ReportStatusEnum.COMPLETED
        db.commit()
        db.refresh(report)
        create_report_timeline_event(db, report)
        return report

    @staticmethod
    def _get_report_by_id(db: Session, report_id: str) -> Report | None:
        try:
            report_uuid = uuid.UUID(report_id)
        except (TypeError, ValueError):
            return None

        return (
            db.query(Report)
            .filter(
                Report.id == report_uuid,
                Report.is_deleted == False,
            )
            .first()
        )

    @staticmethod
    def _get_user_report(db: Session, current_user: User, report_id: str) -> Report:
        try:
            report_uuid = uuid.UUID(report_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report id.") from exc

        report = (
            db.query(Report)
            .filter(
                Report.id == report_uuid,
                Report.user_id == current_user.id,
                Report.is_deleted == False,
            )
            .first()
        )

        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

        return report

    @classmethod
    def _persist_file(cls, user_id: Any, original_name: str, file_bytes: bytes) -> tuple[str, str]:
        """
        Upload a file to Supabase Storage.
        Returns (storage_path, public_url) — same contract as before.
        """
        return _supabase_upload_report(user_id, original_name, file_bytes)

    @classmethod
    def _delete_stored_file(cls, report: Report) -> None:
        summary_data = report.summary_data if isinstance(report.summary_data, dict) else {}
        upload_metadata = summary_data.get("upload_metadata") if isinstance(summary_data.get("upload_metadata"), dict) else {}
        storage_path_value = (
            getattr(report, "storage_path", None)
            or upload_metadata.get("storage_path")
            or cls._storage_path_from_public_url(getattr(report, "file_url", None))
        )
        storage_path = cls._storage_path_from_public_url(storage_path_value) or storage_path_value

        if not storage_path:
            return

        if cls._delete_local_file_if_exists(storage_path):
            return

        if cls._is_legacy_local_storage_path(storage_path):
            return

        _supabase_delete_report(storage_path, getattr(report, "storage_bucket", None))

    @staticmethod
    def _delete_local_file_if_exists(path_value: str) -> bool:
        candidate = Path(path_value)
        search_paths = [candidate] if candidate.is_absolute() else [candidate, Path(settings.REPORT_UPLOAD_DIR) / candidate]

        for path in search_paths:
            try:
                if path.is_file():
                    path.unlink()
                    logger.info("Deleted local report file: %s", path)
                    return True
            except FileNotFoundError:
                return True
            except OSError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unable to delete stored report file: {exc}",
                ) from exc

        return False

    @staticmethod
    def _is_legacy_local_storage_path(path_value: str) -> bool:
        normalized = str(path_value or "").replace("\\", "/").lstrip("./")
        upload_dir = str(settings.REPORT_UPLOAD_DIR or "").replace("\\", "/").strip("/")
        return bool(upload_dir and normalized.startswith(f"{upload_dir}/"))

    @staticmethod
    def _storage_path_from_public_url(file_url: str | None) -> str | None:
        if not file_url:
            return None
        parsed_path = urlparse(file_url).path
        bucket = settings.SUPABASE_BUCKET_NAME
        marker = f"/storage/v1/object/public/{bucket}/"
        if marker in parsed_path:
            return parsed_path.split(marker, 1)[1] or None
        return None

    @classmethod
    async def _analyze_report(cls, filename: str, content_type: str | None, file_bytes: bytes) -> dict[str, Any]:
        mime_type = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        title = Path(filename).stem.replace("_", " ").replace("-", " ").strip().title() or "Medical Report"

        if mime_type == "application/pdf":
            pdf_pages: list[dict[str, Any]] = []
            pdf_warnings: list[str] = []
            try:
                pdf_pages = cls._extract_pdf_pages(file_bytes)
            except Exception as exc:
                logger.info("PDF text extraction unavailable; continuing with OCR: %s", exc)
                pdf_warnings.append(f"pdf_text: {exc}")
            ocr_result = OCRService().extract_text(
                OCRInput(filename=filename, content=file_bytes, content_type=mime_type)
            )
            merged_text, text_pages, text_source = cls._merge_pdf_and_ocr_text(pdf_pages, ocr_result)
            print("Extracted text length:", len(merged_text or ""))
            analysis = cls._build_local_analysis(
                title,
                merged_text,
                source=f"ocr-{ocr_result.provider}" if ocr_result.usable else "pdf-ocr-fallback",
                text_source=text_source,
                ocr_provider=ocr_result.provider,
                ocr_confidence=ocr_result.confidence,
                ocr_warnings=[*pdf_warnings, *ocr_result.warnings],
                text_pages=text_pages,
            )
            return await cls._enrich_analysis_with_prediction(filename, analysis)

        ocr_result = OCRService().extract_text(
            OCRInput(filename=filename, content=file_bytes, content_type=mime_type)
        )
        print("Extracted text length:", len(ocr_result.text or ""))
        analysis = cls._build_ocr_analysis(title, ocr_result, fallback_kind="image")
        return await cls._enrich_analysis_with_prediction(filename, analysis)

    @staticmethod
    def _extract_pdf_text(file_bytes: bytes) -> str:
        return "\n".join(page["text"] for page in ReportService._extract_pdf_pages(file_bytes)).strip()

    @staticmethod
    def _extract_pdf_pages(file_bytes: bytes) -> list[dict[str, Any]]:
        if PdfReader is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF parsing is unavailable in this environment.",
            )
        reader = PdfReader(BytesIO(file_bytes))
        pages: list[dict[str, Any]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(
                    {
                        "page_number": page_number,
                        "text": page_text.strip(),
                        "source_type": "PDF",
                        "confidence": 1.0,
                    }
                )
        return pages

    @staticmethod
    def _ocr_pages(ocr_result: OCRResult) -> list[dict[str, Any]]:
        if ocr_result.pages:
            return [
                {
                    "page_number": page.page_number,
                    "text": page.text.strip(),
                    "source_type": "OCR",
                    "confidence": page.confidence if page.confidence is not None else ocr_result.confidence,
                    "provider": ocr_result.provider,
                    "width": page.width,
                    "height": page.height,
                    "words": [
                        {
                            "text": word.text,
                            "bbox": word.bbox,
                            "confidence": word.confidence,
                            "page_number": word.page_number or page.page_number,
                        }
                        for word in page.words
                        if word.text
                    ],
                    "lines": [
                        {
                            "text": line.text,
                            "bbox": line.bbox,
                            "confidence": line.confidence,
                            "page_number": line.page_number or page.page_number,
                            "words": [
                                {
                                    "text": word.text,
                                    "bbox": word.bbox,
                                    "confidence": word.confidence,
                                    "page_number": word.page_number or page.page_number,
                                }
                                for word in line.words
                                if word.text
                            ],
                        }
                        for line in page.lines
                        if line.text
                    ],
                }
                for page in ocr_result.pages
                if page.text and page.text.strip()
            ]

        if not ocr_result.usable:
            return []

        return [
            {
                "page_number": 1,
                "text": ocr_result.text.strip(),
                "source_type": "OCR",
                "confidence": ocr_result.confidence,
                "provider": ocr_result.provider,
            }
        ]

    @classmethod
    def _merge_pdf_and_ocr_text(
        cls,
        pdf_pages: list[dict[str, Any]],
        ocr_result: OCRResult,
    ) -> tuple[str, list[dict[str, Any]], str]:
        ocr_pages = cls._ocr_pages(ocr_result)
        if ocr_pages:
            merged_pages = list(ocr_pages)
            pdf_by_page = {page["page_number"]: page for page in pdf_pages}
            for page in ocr_pages:
                pdf_page = pdf_by_page.get(page["page_number"])
                if not pdf_page:
                    continue
                pdf_text = str(pdf_page.get("text") or "").strip()
                if pdf_text and not cls._text_is_substantially_included(pdf_text, page["text"]):
                    merged_pages.append(
                        {
                            **pdf_page,
                            "source_type": "PDF",
                            "text": pdf_text,
                            "supplemental": True,
                        }
                    )

            return cls._join_text_pages(merged_pages), merged_pages, "OCR"

        if pdf_pages:
            return cls._join_text_pages(pdf_pages), pdf_pages, "PDF"

        return "", [], ocr_result.source_type or "OCR"

    @staticmethod
    def _text_is_substantially_included(candidate: str, primary: str) -> bool:
        candidate_words = set(re.findall(r"[A-Za-z0-9.%-]+", (candidate or "").lower()))
        primary_words = set(re.findall(r"[A-Za-z0-9.%-]+", (primary or "").lower()))
        if not candidate_words:
            return True
        overlap = len(candidate_words & primary_words) / max(len(candidate_words), 1)
        return overlap >= 0.86

    @staticmethod
    def _join_text_pages(text_pages: list[dict[str, Any]]) -> str:
        parts = []
        for page in text_pages:
            text = str(page.get("text") or "").strip()
            if not text:
                continue
            source = page.get("source_type") or "OCR"
            suffix = " supplemental" if page.get("supplemental") else ""
            parts.append(f"--- Page {page.get('page_number') or 1} {source}{suffix} ---\n{text}")
        return "\n\n".join(parts).strip()

    @staticmethod
    def _build_ocr_layout(text: str, text_pages: list[dict[str, Any]] | None) -> dict[str, Any] | None:
        pages = [page for page in (text_pages or []) if isinstance(page, dict)]
        if not pages or not any(page.get("words") or page.get("lines") for page in pages):
            return None
        return {
            "text": text,
            "words": [word for page in pages for word in page.get("words", []) if isinstance(word, dict)],
            "lines": [line for page in pages for line in page.get("lines", []) if isinstance(line, dict)],
            "pages": pages,
        }

    @classmethod
    def _build_local_analysis(
        cls,
        title: str,
        extracted_text: str,
        source: str = "local-pdf",
        text_source: str = "pdf_text",
        ocr_provider: str | None = None,
        ocr_confidence: float | None = None,
        ocr_warnings: list[str] | None = None,
        text_pages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        normalized_text = re.sub(r"\s+", " ", extracted_text or "").strip()

        if not normalized_text:
            return {
                "title": title,
                "summary": [
                    "This upload could not be clinically summarized because no readable report text was extracted.",
                ],
                "full_text": "",
                "ocr_text": "",
                "markers": [],
                "source": "local-fallback",
                "text_source": text_source,
                "ocr_provider": ocr_provider,
                "ocr_confidence": ocr_confidence,
                "ocr_warnings": ocr_warnings or [],
                "text_pages": text_pages or [],
                "ocr_layout": None,
                "structured_lab_data": cls._empty_structured_lab_data(title),
            }

        markers = cls._extract_markers(normalized_text)
        structured_lab_data = cls._extract_structured_lab_data(
            extracted_text or normalized_text,
            title,
            text_source=text_source,
            ocr_confidence=ocr_confidence,
            text_pages=text_pages,
            fallback_markers=markers,
        )
        summary = cls._summarize_text(normalized_text, structured_lab_data.get("biomarkers") or markers)
        summary_view = cls._build_summary_view(
            normalized_text,
            summary,
            structured_lab_data.get("biomarkers") or markers,
            title,
            source,
        )
        ocr_layout = cls._build_ocr_layout(normalized_text, text_pages)

        return {
            "title": title,
            "summary": summary,
            "patient_summary": " ".join(summary),
            "structured_summary": cls._structured_summary_from_view(summary_view),
            "summary_view": summary_view,
            "full_text": normalized_text,
            "ocr_text": normalized_text[:1200],
            "markers": (structured_lab_data.get("biomarkers") or markers)[:12],
            "biomarkers": structured_lab_data.get("biomarkers") or markers,
            "structured_lab_data": structured_lab_data,
            "source": source,
            "text_source": text_source,
            "ocr_provider": ocr_provider,
            "ocr_confidence": ocr_confidence,
            "ocr_warnings": ocr_warnings or [],
            "text_pages": text_pages or [],
            "ocr_layout": ocr_layout,
        }

    @classmethod
    def _build_ocr_analysis(cls, title: str, ocr_result: OCRResult, fallback_kind: str) -> dict[str, Any]:
        if not ocr_result.usable:
            return {
                "title": title,
                "summary": [
                    f"This {fallback_kind} upload could not be clinically summarized because no readable report text was extracted.",
                ],
                "full_text": "",
                "ocr_text": "",
                "markers": [],
                "source": "local-fallback",
                "text_source": ocr_result.source_type,
                "ocr_provider": ocr_result.provider,
                "ocr_confidence": ocr_result.confidence,
                "ocr_warnings": ocr_result.warnings,
                "text_pages": [],
                "ocr_layout": None,
                "structured_lab_data": cls._empty_structured_lab_data(title),
            }

        return cls._build_local_analysis(
            title,
            ocr_result.text,
            source=f"ocr-{ocr_result.provider}",
            text_source=ocr_result.source_type,
            ocr_provider=ocr_result.provider,
            ocr_confidence=ocr_result.confidence,
            ocr_warnings=ocr_result.warnings,
            text_pages=cls._ocr_pages(ocr_result),
        )

    @staticmethod
    def _summary_lines(value: Any, fallback: list[str] | None = None) -> list[str]:
        if isinstance(value, list):
            lines = [str(item).strip() for item in value if str(item or "").strip()]
        elif isinstance(value, dict):
            findings = value.get("findings") or value.get("key_findings") or []
            notes = value.get("notes")
            lines = ReportService._summary_lines(findings)
            note_lines = ReportService._summary_lines(notes)
            lines = [*lines, *note_lines]
        elif isinstance(value, str):
            lines = [value.strip()] if value.strip() else []
        elif value is None:
            lines = []
        else:
            text = str(value).strip()
            lines = [text] if text else []
        cleaned = [line for line in lines if not ReportService._looks_like_raw_summary_line(line)]
        return cleaned or list(fallback or [])

    @staticmethod
    def _safe_list(value: Any) -> list[Any]:
        if isinstance(value, list):
            return [item for item in value if item is not None and item != ""]
        if value is None or value == "":
            return []
        return [value]

    @classmethod
    async def _enrich_analysis_with_prediction(cls, filename: str, analysis: dict[str, Any]) -> dict[str, Any]:
        extracted_text = str(analysis.get("full_text") or analysis.get("ocr_text") or "").strip()
        if not extracted_text or cls._looks_like_fallback_text(extracted_text):
            return analysis

        enriched = dict(analysis)
        try:
            prediction_response = await PredictionClient().get_prediction(
                {
                    "file_name": filename,
                    "extracted_text": extracted_text,
                }
            )
        except Exception:
            logger.exception("Prediction summary generation failed for report %s", filename)
            return await cls._enrich_analysis_with_clinical_summary(filename, enriched)

        if not prediction_response.get("success") or prediction_response.get("status") != "ready":
            logger.warning(
                "Prediction summary generation returned non-ready response for %s: %s",
                filename,
                prediction_response.get("error") or prediction_response.get("status"),
            )
            return await cls._enrich_analysis_with_clinical_summary(filename, enriched)

        prediction_data = prediction_response.get("data") or {}
        structured_summary = cls._normalize_structured_summary(
            prediction_data.get("structured_summary") or prediction_data.get("summary"),
            fallback_title=Path(filename).stem.replace("_", " ").replace("-", " ").strip().title() or "Medical Report",
            fallback_summary=analysis.get("summary"),
        )
        prediction_summary_view = prediction_data.get("summary_view") if isinstance(prediction_data.get("summary_view"), dict) else {}
        summary_view = cls._summary_view_from_structured_summary(
            structured_summary,
            source=prediction_data.get("summary_source") or prediction_response.get("source") or "prediction-service",
            stored_view=prediction_summary_view,
        )
        generated_summary = cls._summary_lines(
            structured_summary,
            fallback=cls._summary_lines(analysis.get("summary"), fallback=[cls.PROCESSING_SUMMARY]),
        )
        enriched.update(
            {
                "summary": generated_summary,
                "patient_summary": prediction_data.get("patient_summary") or generated_summary[0],
                "structured_summary": structured_summary,
                "summary_view": summary_view,
                "risks": cls._safe_list(prediction_data.get("risks")),
                "risk_level": prediction_data.get("risk_level") or "Low",
                "recommendations": cls._safe_list(prediction_data.get("recommendations")),
                "abnormal_values": cls._safe_list(prediction_data.get("abnormal_values")),
                "extracted_values": cls._safe_list(prediction_data.get("extracted_values")),
                "summary_source": prediction_data.get("summary_source") or prediction_response.get("source") or "prediction-service",
            }
        )
        return await cls._enrich_analysis_with_clinical_summary(filename, enriched)

    @staticmethod
    def _empty_structured_lab_data(title: str = "Medical Report") -> dict[str, Any]:
        return {
            "test_type": title or "Medical Report",
            "biomarkers": [],
            "abnormal_values": [],
        }

    @classmethod
    def _extract_structured_lab_data(
        cls,
        text: str,
        title: str,
        *,
        text_source: str = "PDF",
        ocr_confidence: float | None = None,
        text_pages: list[dict[str, Any]] | None = None,
        fallback_markers: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        biomarkers: list[dict[str, Any]] = []
        try:
            from services.lab_pipeline_service import extract_lab_values, normalize_lab_values

            raw_values = extract_lab_values(
                text,
                source_type=text_source or "PDF",
                source_confidence=ocr_confidence,
                page_metadata=text_pages,
            )
            biomarkers = [
                cls._normalize_summary_biomarker(item)
                for item in normalize_lab_values(raw_values)
                if isinstance(item, dict)
            ]
        except Exception:
            logger.exception("Structured lab extraction failed during report summary generation")

        if not biomarkers and fallback_markers:
            biomarkers = cls._markers_to_structured_biomarkers(fallback_markers)

        test_type = cls._infer_test_type(title, text, biomarkers)
        abnormal_values = [
            cls._clinical_abnormal_value(item)
            for item in biomarkers
            if cls._is_abnormal_status(item.get("status"))
        ]
        structured_data = {
            "test_type": test_type,
            "biomarkers": biomarkers,
            "abnormal_values": abnormal_values,
        }
        cls._log_summary_json("structured_data_input", structured_data)
        return structured_data

    @staticmethod
    def _normalize_summary_biomarker(item: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(item)
        name = str(normalized.get("name") or normalized.get("test_name") or "").lower()
        context = " ".join(
            str(normalized.get(key) or "")
            for key in ("source_text", "source_span")
        ).lower()

        if "mg/dl" in context or "mg %" in context:
            normalized["unit"] = "mg/dL"
        elif "g/dl" in context or "gm/dl" in context or "g%" in context:
            normalized["unit"] = "g/dL"

        if "%" in context and any(token in name for token in ("hba1c", "a1c", "hematocrit")):
            normalized["unit"] = "%"

        if normalized.get("unit") == "g/dL" and any(
            token in name
            for token in (
                "glucose",
                "cholesterol",
                "triglyceride",
                "creatinine",
                "urea",
                "bilirubin",
                "uric acid",
                "calcium",
            )
        ):
            normalized["unit"] = "mg/dL"

        return normalized

    @classmethod
    def _markers_to_structured_biomarkers(cls, markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        biomarkers = []
        for marker in markers:
            if not isinstance(marker, dict):
                continue
            value = cls._safe_float(marker.get("value"))
            if value is None:
                continue
            biomarkers.append(
                {
                    "name": str(marker.get("name") or "Biomarker").strip(),
                    "test_name": str(marker.get("name") or "Biomarker").strip(),
                    "value": value,
                    "unit": str(marker.get("unit") or "").strip(),
                    "reference_range": str(marker.get("reference_range") or "").strip(),
                    "status": str(marker.get("status") or marker.get("flag") or "captured").strip(),
                    "confidence_score": marker.get("confidence_score"),
                }
            )
        return biomarkers

    @classmethod
    async def _enrich_analysis_with_clinical_summary(cls, filename: str, analysis: dict[str, Any]) -> dict[str, Any]:
        structured_data = analysis.get("structured_lab_data")
        if not isinstance(structured_data, dict):
            structured_data = cls._empty_structured_lab_data(analysis.get("title") or filename)

        biomarkers = structured_data.get("biomarkers") if isinstance(structured_data.get("biomarkers"), list) else []
        if not biomarkers:
            return analysis

        rag_context = await cls._retrieve_report_rag_context(structured_data)
        clinical_json = await cls.generate_clinical_summary(structured_data, rag_context)
        if not clinical_json:
            return analysis

        patient_info = {}
        if isinstance(analysis.get("summary_view"), dict):
            patient_info = analysis["summary_view"].get("patient_info") or {}

        summary_lines = cls._summary_lines(
            [clinical_json.get("summary"), *(clinical_json.get("key_findings") or [])],
            fallback=cls._summary_lines(analysis.get("summary")),
        )[:6]
        summary_view = {
            "title": analysis.get("title") or Path(filename).stem,
            "summary": summary_lines[0],
            "patient_info": patient_info,
            "test_type": structured_data.get("test_type") or cls._infer_test_type(str(analysis.get("title") or filename), "", biomarkers),
            "key_findings": summary_lines,
            "biomarkers": biomarkers,
            "abnormal_values": clinical_json.get("abnormal_values") or [],
            "risks": cls._summary_lines(clinical_json.get("clinical_interpretation")),
            "recommendations": clinical_json.get("recommendations") or [],
            "risk_level": clinical_json.get("risk_level") or "Low",
            "notes": cls._summary_lines(clinical_json.get("clinical_interpretation")),
            "source": "clinical-summary-rag-llm",
        }
        structured_summary = {
            "patient": cls._format_patient_info(patient_info),
            "test": summary_view["test_type"],
            "findings": summary_lines,
            "abnormal": clinical_json.get("abnormal_values") or [],
            "notes": clinical_json.get("clinical_interpretation") or "",
            "clinical_interpretation": clinical_json.get("clinical_interpretation") or "",
        }

        enriched = dict(analysis)
        enriched.update(
            {
                "summary": summary_lines,
                "patient_summary": clinical_json.get("summary") or summary_lines[0],
                "structured_summary": structured_summary,
                "summary_view": summary_view,
                "risks": summary_view["risks"],
                "risk_level": summary_view["risk_level"],
                "recommendations": summary_view["recommendations"],
                "abnormal_values": summary_view["abnormal_values"],
                "extracted_values": biomarkers,
                "biomarkers": biomarkers,
                "markers": biomarkers[:12],
                "rag_context": rag_context,
                "clinical_summary_json": clinical_json,
                "summary_source": "clinical-summary-rag-llm",
            }
        )
        cls._log_summary_json("final_summary_json", clinical_json)
        return enriched

    @classmethod
    async def _retrieve_report_rag_context(cls, structured_data: dict[str, Any]) -> dict[str, Any]:
        query = cls._build_report_rag_query(structured_data)
        try:
            from pipelines.rag_pipeline.config import RagSettings
            from pipelines.rag_pipeline.corpus import load_corpus_chunks
            from pipelines.rag_pipeline.keyword import keyword_retrieve
            from pipelines.rag_pipeline.text_cleaning import clean_source_payload

            settings = RagSettings()
            chunks = await asyncio.to_thread(load_corpus_chunks, settings)
            documents = await asyncio.to_thread(keyword_retrieve, query, chunks, limit=min(settings.top_k, 4))
            context = {
                "query": query,
                "source": "rag_keyword",
                "documents": [clean_source_payload(doc.as_dict()) for doc in documents],
                "summary": [clean_source_payload(doc.as_dict()) for doc in documents],
                "top_chunks": [clean_source_payload(doc.as_dict()) for doc in documents],
                "error": None,
            }
        except Exception as exc:
            logger.warning("Report summary RAG retrieval failed: %s", exc)
            context = {
                "query": query,
                "source": "rag_unavailable",
                "documents": [],
                "summary": [],
                "top_chunks": [],
                "error": str(exc),
            }

        cls._log_summary_json("rag_context", context)
        return context

    @staticmethod
    def _build_report_rag_query(structured_data: dict[str, Any]) -> str:
        biomarkers = structured_data.get("biomarkers") if isinstance(structured_data.get("biomarkers"), list) else []
        names = [str(item.get("name") or item.get("test_name") or "").strip() for item in biomarkers if isinstance(item, dict)]
        abnormal_names = [
            name
            for name, item in zip(names, biomarkers, strict=False)
            if isinstance(item, dict) and ReportService._is_abnormal_status(item.get("status"))
        ]
        focus_terms = [
            str(structured_data.get("test_type") or "medical report"),
            "lab interpretation clinical reference ranges",
            "abnormal biomarkers",
            *abnormal_names,
            *names[:8],
            "glucose hba1c cholesterol ldl triglycerides blood pressure cardiovascular diabetes renal thyroid hematology",
        ]
        return " ".join(term for term in focus_terms if term).strip()

    @classmethod
    async def generate_clinical_summary(
        cls,
        structured_data: dict[str, Any],
        rag_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        risk_level = cls._compute_lab_risk_level(structured_data)
        deterministic_payload = cls._fallback_clinical_summary_payload(
            structured_data,
            rag_context or {},
            risk_level=risk_level,
        )
        prompt = cls._clinical_summary_prompt(structured_data, rag_context or {}, risk_level=risk_level)
        llm_payload = await cls._call_report_summary_llm(prompt)
        return cls._normalize_clinical_summary_payload(
            llm_payload,
            fallback=deterministic_payload,
            structured_data=structured_data,
            computed_risk_level=risk_level,
        )

    @staticmethod
    def _clinical_summary_prompt(
        structured_data: dict[str, Any],
        rag_context: dict[str, Any],
        *,
        risk_level: str,
    ) -> str:
        return f"""
You are a clinical-grade medical assistant.

Generate a structured, factual, and conservative clinical report summary.

INPUT:
- Lab results (with values and reference ranges)
- Detected abnormalities
- Retrieved medical knowledge

RULES:
- Do NOT hallucinate values
- Do NOT diagnose
- Interpret only based on given data
- Use medical tone (like a doctor note)
- Be specific, not generic

OUTPUT:

{{
  "summary": "...",
  "key_findings": [...],
  "abnormal_values": [...],
  "clinical_interpretation": "...",
  "risk_level": "...",
  "recommendations": [...]
}}

Interpret:
- Each abnormal value explicitly
- Mention normal findings briefly
- Link interpretation to medical reasoning

Lab results:
{json.dumps(structured_data, indent=2, default=str)}

Retrieved medical knowledge:
{json.dumps((rag_context or {}).get("top_chunks") or (rag_context or {}).get("summary") or [], indent=2, default=str)}

Computed risk floor from lab data:
{risk_level}

Return ONLY valid JSON. Use risk_level as one of LOW, MODERATE, HIGH.
""".strip()

    @staticmethod
    async def _call_report_summary_llm(prompt: str) -> dict[str, Any] | None:
        try:
            from pipelines.rag_pipeline.config import RagSettings

            settings = RagSettings()
            if not settings.ollama_base_url and not (settings.llm_api_base and settings.llm_api_key):
                return None

            from services.chat_service import call_llm

            return await call_llm(prompt)
        except Exception as exc:
            logger.warning("Clinical report summary LLM unavailable: %s", exc)
            return None

    @classmethod
    def _normalize_clinical_summary_payload(
        cls,
        payload: Any,
        *,
        fallback: dict[str, Any],
        structured_data: dict[str, Any],
        computed_risk_level: str,
    ) -> dict[str, Any]:
        source = payload if isinstance(payload, dict) else {}
        summary = cls._clean_sentence(source.get("summary")) or fallback["summary"]
        key_findings = cls._summary_lines(source.get("key_findings"), fallback=fallback["key_findings"])[:6]
        clinical_interpretation = (
            cls._clean_sentence(source.get("clinical_interpretation"))
            or fallback["clinical_interpretation"]
        )
        recommendations = cls._summary_lines(source.get("recommendations"), fallback=fallback["recommendations"])[:5]
        risk_level = cls._stronger_risk_level(
            cls._normalize_risk_label(source.get("risk_level")),
            computed_risk_level,
        )
        abnormal_values = [
            cls._clinical_abnormal_value(item)
            for item in (structured_data.get("biomarkers") or [])
            if isinstance(item, dict) and cls._is_abnormal_status(item.get("status"))
        ]
        return {
            "summary": summary,
            "key_findings": key_findings,
            "abnormal_values": abnormal_values,
            "clinical_interpretation": clinical_interpretation,
            "risk_level": risk_level,
            "recommendations": recommendations,
        }

    @classmethod
    def _fallback_clinical_summary_payload(
        cls,
        structured_data: dict[str, Any],
        rag_context: dict[str, Any],
        *,
        risk_level: str,
    ) -> dict[str, Any]:
        biomarkers = [item for item in (structured_data.get("biomarkers") or []) if isinstance(item, dict)]
        abnormal_values = [cls._clinical_abnormal_value(item) for item in biomarkers if cls._is_abnormal_status(item.get("status"))]
        normal_values = [item for item in biomarkers if not cls._is_abnormal_status(item.get("status"))]
        test_type = str(structured_data.get("test_type") or "medical report")

        if abnormal_values:
            abnormal_text = "; ".join(item["interpretation"].rstrip(".") for item in abnormal_values[:4])
            summary = f"{test_type} shows {len(abnormal_values)} abnormal marker(s): {abnormal_text}."
        else:
            normal_names = ", ".join(str(item.get("name") or item.get("test_name")) for item in normal_values[:4] if item.get("name") or item.get("test_name"))
            summary = f"{test_type} shows measured markers within their stated reference ranges"
            summary += f", including {normal_names}." if normal_names else "."

        key_findings = [item["interpretation"] for item in abnormal_values[:4]]
        if normal_values:
            normal_names = ", ".join(cls._format_biomarker_value(item) for item in normal_values[:3])
            if normal_names:
                key_findings.append(f"Other reviewed markers were within range: {normal_names}.")
        if not key_findings:
            key_findings = [summary]

        rag_titles = [
            str(item.get("title") or item.get("source") or "").strip()
            for item in (rag_context.get("top_chunks") or rag_context.get("summary") or [])
            if isinstance(item, dict) and (item.get("title") or item.get("source"))
        ]
        knowledge_note = f" Retrieved context referenced {', '.join(rag_titles[:2])}." if rag_titles else ""
        clinical_interpretation = (
            "The interpretation is based only on extracted values and the reference ranges printed in the report. "
            f"{'Abnormal markers should be correlated with symptoms, history, medicines, and prior trends.' if abnormal_values else 'No extracted marker shows a clear out-of-range pattern.'}"
            f"{knowledge_note}"
        )
        recommendations = cls._recommendations_for_lab_summary(abnormal_values, normal_values, risk_level)
        return {
            "summary": summary,
            "key_findings": key_findings[:6],
            "abnormal_values": abnormal_values,
            "clinical_interpretation": clinical_interpretation,
            "risk_level": risk_level,
            "recommendations": recommendations,
        }

    @classmethod
    def _recommendations_for_lab_summary(
        cls,
        abnormal_values: list[dict[str, Any]],
        normal_values: list[dict[str, Any]],
        risk_level: str,
    ) -> list[str]:
        if not abnormal_values:
            return [
                "Review these results during routine care, especially if symptoms are present or prior values are trending upward or downward.",
            ]

        names = " ".join(str(item.get("name") or "").lower() for item in abnormal_values)
        recommendations = [
            "Discuss the abnormal result(s) with a clinician, using prior reports and current symptoms for context.",
        ]
        if any(token in names for token in ("glucose", "hba1c", "a1c")):
            recommendations.append("Confirm glucose-related abnormalities with appropriate fasting glucose, HbA1c, or repeat testing as advised by a clinician.")
        if any(token in names for token in ("cholesterol", "ldl", "hdl", "triglyceride")):
            recommendations.append("Review cardiovascular risk factors and lipid management options with a clinician.")
        if any(token in names for token in ("creatinine", "urea", "bun", "sodium", "potassium")):
            recommendations.append("Correlate kidney or electrolyte abnormalities with hydration status, medicines, and repeat testing if clinically indicated.")
        if any(token in names for token in ("hemoglobin", "wbc", "platelet")):
            recommendations.append("Interpret blood-count abnormalities with symptoms, infection signs, bleeding history, and previous CBC trends.")
        if risk_level == "High":
            recommendations.append("Arrange prompt medical review, especially if symptoms are present or the abnormality is new.")
        return recommendations[:5]

    @staticmethod
    def _is_abnormal_status(status: Any) -> bool:
        return str(status or "").strip().lower() in {"high", "low", "borderline", "abnormal", "critical"}

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(str(value).replace("<", "").replace(">", "").strip())
        except (TypeError, ValueError):
            return None

    @classmethod
    def _clinical_abnormal_value(cls, item: dict[str, Any]) -> dict[str, Any]:
        value_text = cls._format_biomarker_value(item)
        status = str(item.get("status") or "abnormal").strip().lower()
        reference = str(item.get("reference_range") or "").strip()
        direction = "above" if status in {"high", "critical"} else "below" if status == "low" else "outside"
        if status == "borderline":
            direction = "near the edge of"
        interpretation = f"{value_text} is {direction} the reference range"
        if reference:
            interpretation += f" ({reference})"
        interpretation += "."
        return {
            "name": item.get("name") or item.get("test_name"),
            "value": item.get("value"),
            "unit": item.get("unit"),
            "reference_range": reference,
            "status": item.get("status"),
            "severity": cls._biomarker_deviation(item)[1],
            "interpretation": interpretation,
        }

    @staticmethod
    def _format_biomarker_value(item: dict[str, Any]) -> str:
        name = str(item.get("name") or item.get("test_name") or "Biomarker").strip()
        value = item.get("value")
        unit = str(item.get("unit") or "").strip()
        value_text = f"{value:g}" if isinstance(value, float) and value.is_integer() else str(value)
        return f"{name} {value_text}{(' ' + unit) if unit else ''}".strip()

    @classmethod
    def _compute_lab_risk_level(cls, structured_data: dict[str, Any]) -> str:
        biomarkers = [item for item in (structured_data.get("biomarkers") or []) if isinstance(item, dict)]
        abnormal = [item for item in biomarkers if cls._is_abnormal_status(item.get("status"))]
        if not abnormal:
            return "Low"

        severities = [cls._biomarker_deviation(item)[1] for item in abnormal]
        critical = any(severity == "critical" or cls._is_known_critical_marker(item) for item, severity in zip(abnormal, severities, strict=False))
        meaningful_abnormal = [item for item, severity in zip(abnormal, severities, strict=False) if severity in {"moderate", "critical"}]
        risk_marker_count = sum(1 for item in abnormal if cls._is_known_risk_marker(item))

        if critical or len(abnormal) >= 3 or (len(meaningful_abnormal) >= 2 and risk_marker_count >= 1):
            return "High"
        if len(meaningful_abnormal) >= 1 or len(abnormal) >= 2 or risk_marker_count >= 1:
            return "Moderate"
        return "Low"

    @classmethod
    def _biomarker_deviation(cls, item: dict[str, Any]) -> tuple[float, str]:
        value = cls._safe_float(item.get("value"))
        reference = str(item.get("reference_range") or "").strip()
        status = str(item.get("status") or "").strip().lower()
        if value is None:
            return 0.0, "minor" if status == "borderline" else "moderate"

        deviation = 0.0
        lt = re.match(r"^<\s*([0-9]+(?:\.[0-9]+)?)$", reference)
        gt = re.match(r"^>\s*([0-9]+(?:\.[0-9]+)?)$", reference)
        rng = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*(?:-|to)\s*([0-9]+(?:\.[0-9]+)?)$", reference, flags=re.IGNORECASE)
        if lt:
            high = float(lt.group(1))
            deviation = max(0.0, (value - high) / max(high, 1.0))
        elif gt:
            low = float(gt.group(1))
            deviation = max(0.0, (low - value) / max(low, 1.0))
        elif rng:
            low, high = float(rng.group(1)), float(rng.group(2))
            if value < low:
                deviation = (low - value) / max(low, 1.0)
            elif value > high:
                deviation = (value - high) / max(high, 1.0)

        if status == "critical" or deviation >= 0.35:
            return deviation, "critical"
        if status in {"high", "low", "abnormal"} or deviation >= 0.15:
            return deviation, "moderate"
        return deviation, "minor"

    @classmethod
    def _is_known_risk_marker(cls, item: dict[str, Any]) -> bool:
        name = str(item.get("name") or item.get("test_name") or "").lower()
        return any(
            token in name
            for token in (
                "bp",
                "blood pressure",
                "glucose",
                "hba1c",
                "a1c",
                "cholesterol",
                "ldl",
                "hdl",
                "triglyceride",
            )
        )

    @classmethod
    def _is_known_critical_marker(cls, item: dict[str, Any]) -> bool:
        name = str(item.get("name") or item.get("test_name") or "").lower()
        value = cls._safe_float(item.get("value"))
        if value is None:
            return False
        if "hba1c" in name or "a1c" in name:
            return value >= 6.5
        if "fasting" in name and "glucose" in name:
            return value >= 126
        if "random" in name and "glucose" in name:
            return value >= 200
        if "ldl" in name:
            return value >= 190
        if "triglyceride" in name:
            return value >= 500
        if "cholesterol" in name and "hdl" not in name and "ldl" not in name:
            return value >= 240
        if "systolic" in name or name == "bp":
            return value >= 160
        if "diastolic" in name:
            return value >= 100
        return False

    @staticmethod
    def _normalize_risk_label(value: Any) -> str | None:
        text = str(value or "").strip().lower()
        if text in {"high", "critical"}:
            return "High"
        if text in {"moderate", "medium"}:
            return "Moderate"
        if text == "low":
            return "Low"
        return None

    @classmethod
    def _stronger_risk_level(cls, candidate: str | None, computed: str) -> str:
        order = {"Low": 0, "Moderate": 1, "High": 2}
        candidate = candidate if candidate in order else computed
        return candidate if order[candidate] >= order.get(computed, 0) else computed

    @staticmethod
    def _clean_sentence(value: Any) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            return ""
        if text[-1] not in ".!?":
            text += "."
        return text

    @staticmethod
    def _log_summary_json(label: str, payload: Any) -> None:
        try:
            logger.info("report_summary_%s=%s", label, json.dumps(payload, default=str)[:4000])
        except Exception:
            logger.info("report_summary_%s=<unserializable>", label)

    @staticmethod
    def _load_lab_pipeline_runner() -> Callable[[str], Any]:
        try:
            from apps.backend.services.lab_pipeline_service import run_lab_pipeline
        except ImportError:
            from services.lab_pipeline_service import run_lab_pipeline

        return run_lab_pipeline

    @classmethod
    def _schedule_lab_pipeline(
        cls,
        report_id: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> None:
        try:
            runner = cls._load_lab_pipeline_runner()
            if background_tasks is not None:
                background_tasks.add_task(runner, report_id)
                return

            asyncio.create_task(asyncio.to_thread(runner, report_id))
        except Exception:
            logger.exception("Failed to schedule lab pipeline for report %s", report_id)

    @staticmethod
    def _extract_markers(text: str) -> list[dict[str, str]]:
        # NOTE: every unit group MUST be a capturing group (...)
        # so that match.group(2) is always safe when the pattern matches.
        marker_patterns = [
            ("Hemoglobin",  r"hemoglobin[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(g/dl|gm/dl|g%)?"),
            ("WBC",         r"(?:wbc|white blood cells?)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(/mm3|cells/?u?l|10\^3/?u?l)?"),
            ("RBC",         r"(?:rbc|red blood cells?)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(million/?u?l|10\^6/?u?l)?"),
            ("Platelets",   r"(?:platelets?)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(lakhs/?cumm|10\^3/?u?l|/mm3)?"),
            ("Glucose",     r"(?:glucose|blood sugar|fasting glucose)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(mg/dl)?"),
            ("HbA1c",       r"(?:hba1c|a1c)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(%)?"),
            ("Creatinine",  r"creatinine[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(mg/dl)?"),
            ("Urea",        r"(?:urea|blood urea)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(mg/dl)?"),
            ("TSH",         r"tsh[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(uiu/ml|miu/l|miu/l)?"),
            ("Vitamin D",   r"(?:vitamin d|25-oh vitamin d)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(ng/ml)?"),
            ("Cholesterol", r"(?:total cholesterol|cholesterol)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(mg/dl)?"),
        ]

        markers = []
        lowered = text.lower()
        for name, pattern in marker_patterns:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if not match:
                continue
            unit = (match.group(2) if match.lastindex and match.lastindex >= 2 else None) or ""
            markers.append(
                {
                    "name": name,
                    "value": match.group(1) or "",
                    "unit": unit.strip(),
                    "flag": "captured",
                }
            )
        return markers

    @staticmethod
    def _looks_like_raw_summary_line(text: str) -> bool:
        normalized = re.sub(r"\s+", " ", str(text or "")).strip().lower()
        return (
            not normalized
            or normalized.startswith("preview:")
            or normalized.startswith("--- page ")
            or "extracted text is available in the ocr tab" in normalized
        )

    @staticmethod
    def _format_patient_info(patient_info: Any) -> str:
        if isinstance(patient_info, str):
            return patient_info.strip()
        if isinstance(patient_info, dict):
            labels = {
                "patient_name": "Name",
                "name": "Name",
                "age": "Age",
                "sex": "Sex",
                "gender": "Gender",
                "patient_id": "Patient ID",
                "report_date": "Report Date",
            }
            parts = []
            for key, value in patient_info.items():
                rendered = str(value or "").strip()
                if rendered:
                    parts.append(f"{labels.get(key, str(key).replace('_', ' ').title())}: {rendered}")
            return "; ".join(parts)
        return ""

    @classmethod
    def _infer_test_type(cls, title: str, text: str = "", markers: list[dict[str, Any]] | None = None) -> str:
        marker_names = " ".join(str(marker.get("name") or "") for marker in (markers or []))
        source = f"{title} {marker_names} {text}".lower()
        if any(term in source for term in ["complete blood count", "cbc", "hemoglobin", "wbc", "platelet"]):
            return "Complete Blood Count"
        if any(term in source for term in ["lipid profile", "cholesterol", "triglyceride", "hdl", "ldl"]):
            return "Lipid Profile"
        if any(term in source for term in ["hba1c", "fasting glucose", "blood sugar", "glucose"]):
            return "Glucose / Diabetes Panel"
        if any(term in source for term in ["thyroid", "tsh", "t3", "t4"]):
            return "Thyroid Function Test"
        if any(term in source for term in ["creatinine", "urea", "kidney", "renal"]):
            return "Renal Function Test"
        if "xray" in source or "x-ray" in source:
            return "Radiology Report"
        return "Medical Report"

    @classmethod
    def _normalize_structured_summary(
        cls,
        value: Any,
        fallback_title: str = "Medical Report",
        fallback_summary: Any = None,
    ) -> dict[str, Any]:
        if isinstance(value, dict):
            findings = cls._summary_lines(value.get("findings") or value.get("key_findings"))
            notes_lines = cls._summary_lines(value.get("notes"))
            notes = " ".join(notes_lines).strip()
            abnormal = cls._safe_list(value.get("abnormal") or value.get("abnormal_values"))
            patient = cls._format_patient_info(value.get("patient") or value.get("patient_info"))
            test = str(value.get("test") or value.get("test_type") or value.get("title") or fallback_title).strip()
        else:
            findings = cls._summary_lines(value, fallback=cls._summary_lines(fallback_summary))
            notes = ""
            abnormal = []
            patient = ""
            test = fallback_title

        if not findings:
            findings = cls._summary_lines(fallback_summary, fallback=[cls.PROCESSING_SUMMARY])

        return {
            "patient": patient,
            "test": test or "Medical Report",
            "findings": findings,
            "abnormal": abnormal,
            "notes": notes,
        }

    @classmethod
    def _summary_view_from_structured_summary(
        cls,
        structured_summary: dict[str, Any],
        source: str,
        stored_view: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        stored_view = stored_view or {}
        findings = cls._summary_lines(
            stored_view.get("key_findings") or structured_summary.get("findings"),
            fallback=[cls.PROCESSING_SUMMARY],
        )
        abnormal_values = cls._safe_list(stored_view.get("abnormal_values") or structured_summary.get("abnormal"))
        notes = cls._summary_lines(stored_view.get("notes") or structured_summary.get("notes"))
        test_type = str(stored_view.get("test_type") or structured_summary.get("test") or "Medical Report").strip()

        return {
            "title": stored_view.get("title") or test_type,
            "summary": stored_view.get("summary") or findings[0],
            "patient_info": stored_view.get("patient_info") or structured_summary.get("patient") or "",
            "test_type": test_type,
            "key_findings": findings,
            "biomarkers": stored_view.get("biomarkers") or [],
            "abnormal_values": abnormal_values,
            "risks": stored_view.get("risks") or [],
            "recommendations": stored_view.get("recommendations") or [],
            "risk_level": stored_view.get("risk_level") or "Low",
            "notes": notes,
            "source": stored_view.get("source") or source,
        }

    @staticmethod
    def _structured_summary_from_view(summary_view: dict[str, Any]) -> dict[str, Any]:
        notes = summary_view.get("notes") or []
        return {
            "patient": ReportService._format_patient_info(summary_view.get("patient_info")),
            "test": str(summary_view.get("test_type") or summary_view.get("title") or "Medical Report").strip(),
            "findings": ReportService._summary_lines(summary_view.get("key_findings")),
            "abnormal": ReportService._safe_list(summary_view.get("abnormal_values")),
            "notes": " ".join(ReportService._summary_lines(notes)).strip(),
        }

    @staticmethod
    def _summarize_text(text: str, markers: list[dict[str, str]]) -> list[str]:
        line_one = "Readable report text was extracted and structured for clinical review."

        if markers:
            marker_names = ", ".join(marker["name"] for marker in markers[:3])
            line_two = f"Detected key report markers including {marker_names}."
        else:
            line_two = "Readable report text was found, but no standard biomarker pattern was confidently detected."

        return [line_one, line_two]

    @staticmethod
    def _safe_filename(filename: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", filename or "report")
        return cleaned.strip("-") or "report"

    @staticmethod
    def _strip_uuid_prefix(filename: str) -> str:
        return re.sub(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}-",
            "",
            filename or "",
        )

    @classmethod
    def _stored_filename(cls, storage_path: str | None = None, file_url: str | None = None) -> str | None:
        source = storage_path or urlparse(file_url or "").path
        if not source:
            return None
        filename = Path(str(source).split("?", 1)[0].split("#", 1)[0]).name
        return filename or None

    @staticmethod
    def _report_name(file_url: str, fallback_name: str | None = None) -> str:
        if fallback_name:
            return fallback_name
        parsed_path = urlparse(file_url or "").path
        file_name = Path(parsed_path).name if parsed_path else ""
        return ReportService._strip_uuid_prefix(file_name) or "Medical Report"

    @classmethod
    def _serialize_report(cls, report: Report) -> dict[str, Any]:
        summary_data = report.summary_data if isinstance(report.summary_data, dict) else {}
        upload_metadata = summary_data.get("upload_metadata") if isinstance(summary_data.get("upload_metadata"), dict) else {}
        stored_filename = (
            getattr(report, "stored_filename", None)
            or upload_metadata.get("stored_filename")
            or cls._stored_filename(getattr(report, "storage_path", None) or upload_metadata.get("storage_path"), report.file_url)
        )
        file_name = (
            getattr(report, "original_filename", None)
            or upload_metadata.get("original_filename")
            or upload_metadata.get("file_name")
            or cls._strip_uuid_prefix(stored_filename or "")
            or cls._report_name(report.file_url)
        )
        file_size = None
        parsed_path = urlparse(report.file_url or "").path.lstrip("/")
        parsed_text = (report.parsed_text or "").strip()
        if summary_data:
            ocr_text = summary_data.get("ocr_text", parsed_text)
            summary_lines = cls._summary_lines(
                summary_data.get("summary") or summary_data.get("patient_summary"),
                fallback=[cls.PROCESSING_SUMMARY],
            )
            risks = cls._safe_list(summary_data.get("risks") or summary_data.get("risk_analysis"))
            recommendations = cls._safe_list(summary_data.get("recommendations"))
            structured_summary = cls._normalize_structured_summary(
                summary_data.get("structured_summary") or summary_data.get("summary"),
                fallback_title=file_name,
                fallback_summary=summary_lines,
            )
            abnormal_values = cls._safe_list(summary_data.get("abnormal_values") or structured_summary.get("abnormal"))
            
            analysis = {
                "title": summary_data.get("title", file_name),
                "summary": summary_lines,
                "ocr_text": ocr_text,
                "markers": summary_data.get("markers") or summary_data.get("biomarkers") or [],
                "source": summary_data.get("summary_source") or summary_data.get("source", "prediction-service"),
                "risks": risks,
                "risk_level": summary_data.get("risk_level") or "Low",
                "recommendations": recommendations,
                "abnormal_values": abnormal_values,
            }
            stored_summary_view = summary_data.get("summary_view") if isinstance(summary_data.get("summary_view"), dict) else {}
            summary_view = {
                "title": stored_summary_view.get("title") or analysis["title"],
                "summary": stored_summary_view.get("summary") or summary_lines[0],
                "patient_info": stored_summary_view.get("patient_info") or structured_summary.get("patient") or summary_data.get("patient_info", {}),
                "test_type": stored_summary_view.get("test_type") or structured_summary.get("test") or cls._infer_test_type(analysis["title"], parsed_text, analysis["markers"]),
                "key_findings": cls._summary_lines(stored_summary_view.get("key_findings"), fallback=analysis["summary"]),
                "biomarkers": stored_summary_view.get("biomarkers") or analysis["markers"],
                "abnormal_values": stored_summary_view.get("abnormal_values") or abnormal_values,
                "risks": stored_summary_view.get("risks") or risks,
                "recommendations": stored_summary_view.get("recommendations") or recommendations,
                "risk_level": stored_summary_view.get("risk_level") or analysis["risk_level"],
                "notes": stored_summary_view.get("notes") or cls._summary_lines(structured_summary.get("notes") or summary_data.get("notes")),
                "source": stored_summary_view.get("source") or analysis["source"],
            }
            date_of_report = upload_metadata.get("date_of_report")
        elif parsed_text and not cls._looks_like_fallback_text(parsed_text):
            analysis = cls._build_local_analysis(file_name, parsed_text)
            summary_view = cls._build_summary_view(
                analysis["ocr_text"],
                analysis["summary"],
                analysis["markers"],
                analysis["title"],
                analysis["source"],
            )
            date_of_report = None
        elif parsed_text:
            analysis = {
                "title": file_name,
                "summary": [],
                "ocr_text": parsed_text,
                "markers": [],
                "source": "local-fallback",
                "risks": [],
                "risk_level": "Low",
                "recommendations": [],
                "abnormal_values": [],
            }
            summary_view = cls._build_summary_view(
                analysis["ocr_text"], [], [], file_name, "local-fallback"
            )
            date_of_report = None
        else:
            analysis = {
                "title": file_name,
                "summary": [],
                "ocr_text": "",
                "markers": [],
                "source": "stored-empty",
                "risks": [],
                "risk_level": "Low",
                "recommendations": [],
                "abnormal_values": [],
            }
            summary_view = cls._build_summary_view("", [], [], file_name, "stored-empty")
            date_of_report = None
        if parsed_path:
            # File is now in Supabase Storage — cannot stat remote files.
            # file_size was already captured at upload time and stored by callers.
            file_size = upload_metadata.get("file_size")

        return {
            "id": str(report.id),
            "name": file_name,
            "file_name": file_name,
            "original_filename": file_name,
            "stored_filename": stored_filename,
            "file_url": report.file_url,
            "report_type": report.report_type.value,
            "status": report.status.value,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
            "file_size": file_size,
            "storage_path": report.storage_path or upload_metadata.get("storage_path"),
            "parsed_text": report.parsed_text,
            "ocr_text": analysis["ocr_text"],
            "summary": analysis["summary"],
            "patient_summary": summary_data.get("patient_summary") or (analysis["summary"][0] if analysis["summary"] else cls.PROCESSING_SUMMARY),
            "risks": analysis.get("risks", []),
            "risk_level": analysis.get("risk_level", "Low"),
            "recommendations": analysis.get("recommendations", []),
            "abnormal_values": analysis.get("abnormal_values", []),
            "markers": analysis["markers"],
            "summary_source": analysis["source"],
            "text_source": (report.summary_data or {}).get("text_source") if isinstance(report.summary_data, dict) else None,
            "ocr_provider": (report.summary_data or {}).get("ocr_provider") if isinstance(report.summary_data, dict) else None,
            "ocr_confidence": (report.summary_data or {}).get("ocr_confidence") if isinstance(report.summary_data, dict) else None,
            "summary_view": summary_view,
            "structured_summary": cls._structured_summary_from_view(summary_view),
            "summary_data": report.summary_data or {},
            "date_of_report": date_of_report,
        }

    @staticmethod
    def _build_processing_summary_view(title: str) -> dict[str, Any]:
        return {
            "title": title,
            "summary": ReportService.PROCESSING_SUMMARY,
            "patient_info": {},
            "key_findings": [ReportService.PROCESSING_SUMMARY],
            "biomarkers": [],
            "abnormal_values": [],
            "notes": [],
            "source": "background-processing",
        }

    @classmethod
    def _build_summary_view(
        cls,
        extracted_text: str,
        summary_lines: list[str],
        markers: list[dict[str, str]],
        title: str,
        source: str,
    ) -> dict[str, Any]:
        normalized_text = re.sub(r"\s+", " ", extracted_text or "").strip()
        safe_summary_lines = cls._summary_lines(summary_lines, fallback=[cls.PROCESSING_SUMMARY])
        if not normalized_text or source == "local-fallback":
            return {
                "title": title,
                "summary": safe_summary_lines[0],
                "patient_info": {},
                "test_type": cls._infer_test_type(title, "", markers),
                "key_findings": safe_summary_lines,
                "biomarkers": [],
                "abnormal_values": [],
                "notes": ["Readable report text is required before clinical interpretation."],
                "source": source,
            }

        return {
            "title": title,
            "summary": safe_summary_lines[0],
            "patient_info": cls._extract_patient_info(extracted_text),
            "test_type": cls._infer_test_type(title, extracted_text, markers),
            "key_findings": safe_summary_lines,
            "biomarkers": [marker for marker in markers if marker],
            "abnormal_values": [],
            "notes": [],
            "source": source,
        }

    @staticmethod
    def _extract_patient_info(text: str) -> dict[str, str]:
        if not text:
            return {}

        patterns = {
            "patient_name": r"(?:patient name|name)\s*[:\-]\s*([^\n,;|]{2,80})",
            "age": r"\bage\s*[:\-]\s*([0-9]{1,3}(?:\s*(?:years?|yrs?))?)",
            "sex": r"(?:sex|gender)\s*[:\-]\s*([A-Za-z]{3,10})",
            "patient_id": r"(?:patient id|id)\s*[:\-]\s*([A-Za-z0-9-]{2,40})",
            "report_date": r"(?:report date|date of report|date)\s*[:\-]\s*([A-Za-z0-9,/\- ]{4,40})",
        }

        extracted: dict[str, str] = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                value = re.split(
                    r"\b(?:age|sex|gender|patient id|report date|date|complete blood count|cbc|hemoglobin|wbc|platelet|glucose|cholesterol)\b",
                    match.group(1),
                    maxsplit=1,
                    flags=re.IGNORECASE,
                )[0]
                value = value.strip()
                if value:
                    extracted[key] = value
        return extracted

    @staticmethod
    def _extract_notes(text: str) -> list[str]:
        if not text:
            return []

        sentences = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", text) if segment.strip()]
        if sentences:
            note = " ".join(sentences[:2]).strip()
        else:
            words = text.split()
            note = " ".join(words[:35]).strip()

        if not note:
            return []

        return [note[:240] + ("..." if len(note) > 240 else "")]

    @staticmethod
    def _looks_like_fallback_text(text: str) -> bool:
        lowered = (text or "").lower()
        return any(
            marker in lowered
            for marker in [
                "image ocr is not configured on this machine yet",
                "no text could be extracted from this pdf",
                "free mode currently supports direct text extraction from pdf reports",
                "pdf uploaded and stored successfully",
                "report uploaded and stored successfully",
            ]
        )

    @staticmethod
    def _validate_report_type(report_type: str) -> None:
        allowed = {item.value for item in ReportTypeEnum}
        if report_type not in allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report type.")

    @staticmethod
    def _normalize_report_date(value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text).isoformat()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_of_report must be in YYYY-MM-DD format.",
            ) from exc
