import asyncio
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
                    "Report uploaded and stored successfully.",
                    "No readable text was found in this file.",
                    "OCR providers returned no usable text for this upload.",
                ],
                "full_text": "",
                "ocr_text": "No text could be extracted from this report.",
                "markers": [],
                "source": "local-fallback",
                "text_source": text_source,
                "ocr_provider": ocr_provider,
                "ocr_confidence": ocr_confidence,
                "ocr_warnings": ocr_warnings or [],
                "text_pages": text_pages or [],
                "ocr_layout": None,
            }

        markers = cls._extract_markers(normalized_text)
        summary = cls._summarize_text(normalized_text, markers)
        summary_view = cls._build_summary_view(
            normalized_text,
            summary,
            markers,
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
            "markers": markers[:6],
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
                    f"{fallback_kind} report uploaded and stored successfully.",
                    "No readable text was returned by the configured OCR providers.",
                    "Check Google Vision credentials or local Tesseract installation before reprocessing.",
                ],
                "full_text": "",
                "ocr_text": "No text could be extracted from this report.",
                "markers": [],
                "source": "local-fallback",
                "text_source": ocr_result.source_type,
                "ocr_provider": ocr_result.provider,
                "ocr_confidence": ocr_result.confidence,
                "ocr_warnings": ocr_result.warnings,
                "text_pages": [],
                "ocr_layout": None,
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

        try:
            prediction_response = await PredictionClient().get_prediction(
                {
                    "file_name": filename,
                    "extracted_text": extracted_text,
                }
            )
        except Exception:
            logger.exception("Prediction summary generation failed for report %s", filename)
            return analysis

        if not prediction_response.get("success") or prediction_response.get("status") != "ready":
            logger.warning(
                "Prediction summary generation returned non-ready response for %s: %s",
                filename,
                prediction_response.get("error") or prediction_response.get("status"),
            )
            return analysis

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
        enriched = dict(analysis)
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
        return enriched

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
            "patient": patient or "Not specified in the uploaded report.",
            "test": test or "Medical Report",
            "findings": findings,
            "abnormal": abnormal,
            "notes": notes or "Clinical review is recommended for diagnosis, treatment decisions, and comparison with prior reports.",
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
            "patient_info": stored_view.get("patient_info") or structured_summary.get("patient") or "Not specified in the uploaded report.",
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
            "patient": ReportService._format_patient_info(summary_view.get("patient_info")) or "Not specified in the uploaded report.",
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
                "notes": ["Clinical review is recommended once readable report text is available."],
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
            "notes": ["Clinical review is recommended for diagnosis, treatment decisions, and comparison with prior reports."],
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
