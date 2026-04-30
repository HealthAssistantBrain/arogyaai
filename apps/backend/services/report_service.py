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

from core.pipeline_logger import log_pipeline
from integrations.supabase_storage import upload_report as _supabase_upload_report
from models import Report, ReportStatusEnum, ReportTypeEnum, User
from services.notification_service import trigger_notification

logger = logging.getLogger("uvicorn.error")


class ReportService:
    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

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
        extension = Path(file.filename or "").suffix.lower()
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
        storage_path, public_url = cls._persist_file(current_user.id, file.filename, file_bytes)
        log_pipeline("report", step="upload_file", status="healthy", data="stored")

        report = Report(
            user_id=current_user.id,
            report_type=ReportTypeEnum(report_type),
            file_url=public_url,
            summary_data={"upload_metadata": {"date_of_report": normalized_report_date}} if normalized_report_date else None,
            status=ReportStatusEnum.PROCESSING,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        try:
            log_pipeline("report", step="analyze_report", status="running", data="pending")
            analysis = await cls._analyze_report(file.filename or "report", file.content_type, file_bytes)
            cls.persist_report(db, str(report.id), analysis.get("full_text") or analysis.get("ocr_text", ""), analysis)
            cls._schedule_lab_pipeline(str(report.id), background_tasks=background_tasks)
            db.refresh(report)
            try:
                await trigger_notification(
                    user_id=str(current_user.id),
                    event_type="health_alert",
                    title="Lab Report Processed",
                    message="Your medical report has been analyzed.",
                    data={
                        "report_id": str(report.id),
                        "report_type": report.report_type.value,
                        "summary": "Your uploaded report is ready for review in ArogyaAI.",
                        "url": "/lab-results",
                        "severity": "info",
                    },
                )
            except Exception:
                logger.exception("Failed to trigger processed-report notification for report %s", report.id)
            log_pipeline("report", step="analyze_report", status="healthy", data="fetched",
                         extra=f"source={analysis.get('source', '?')}")
        except Exception as exc:
            report.status = ReportStatusEnum.FAILED
            db.commit()
            db.refresh(report)
            log_pipeline("report", step="analyze_report", status="unhealthy", data="failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Report was saved, but summarization failed: {exc}",
            ) from exc

        return {
            "success": True,
            "status": "ready",
            "error": None,
            "data": {
                "id": str(report.id),
                "name": cls._report_name(report.file_url, file.filename),
                "file_name": file.filename,
                "file_size": len(file_bytes),
                "report_type": report.report_type.value,
                "file_url": report.file_url,
                "status": report.status.value,
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "updated_at": report.updated_at.isoformat() if report.updated_at else None,
                "storage_path": str(storage_path),
                "title": analysis["title"],
                "summary": analysis["summary"],
                "ocr_text": analysis["ocr_text"],
                "markers": analysis["markers"],
                "summary_source": analysis["source"],
                "date_of_report": normalized_report_date,
                "summary_view": cls._build_summary_view(
                    analysis["ocr_text"],
                    analysis["summary"],
                    analysis["markers"],
                    analysis["title"],
                    analysis["source"],
                ),
            },
        }

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

        report.parsed_text = parsed_text
        report.summary_data = merged_summary
        report.status = ReportStatusEnum.COMPLETED
        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def _persist_file(cls, user_id: Any, original_name: str, file_bytes: bytes) -> tuple[str, str]:
        """
        Upload a file to Supabase Storage.
        Returns (storage_path, public_url) — same contract as before.
        """
        return _supabase_upload_report(user_id, original_name, file_bytes)

    @classmethod
    async def _analyze_report(cls, filename: str, content_type: str | None, file_bytes: bytes) -> dict[str, Any]:
        mime_type = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        title = Path(filename).stem.replace("_", " ").replace("-", " ").strip().title() or "Medical Report"

        if mime_type == "application/pdf":
            extracted_text = cls._extract_pdf_text(file_bytes)
            return cls._build_local_analysis(title, extracted_text)

        return {
            "title": title,
            "summary": [
                "Image report uploaded and stored successfully.",
                "Free mode currently supports direct text extraction from PDF reports.",
                "For JPG or PNG reports, install Tesseract OCR and I can wire image reading too.",
            ],
            "full_text": "",
            "ocr_text": "Image OCR is not configured on this machine yet.",
            "markers": [],
            "source": "local-fallback",
        }

    @staticmethod
    def _extract_pdf_text(file_bytes: bytes) -> str:
        if PdfReader is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF parsing is unavailable in this environment.",
            )
        reader = PdfReader(BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text.strip())
        return "\n".join(text_parts).strip()

    @classmethod
    def _build_local_analysis(cls, title: str, extracted_text: str) -> dict[str, Any]:
        normalized_text = re.sub(r"\s+", " ", extracted_text or "").strip()

        if not normalized_text:
            return {
                "title": title,
                "summary": [
                    "PDF uploaded and stored successfully.",
                    "No readable text was found in this PDF in free mode.",
                    "If this is a scanned PDF, install Tesseract OCR and I can enable scanned-document extraction.",
                ],
                "full_text": "",
                "ocr_text": "No text could be extracted from this PDF.",
                "markers": [],
                "source": "local-fallback",
            }

        markers = cls._extract_markers(normalized_text)
        summary = cls._summarize_text(normalized_text, markers)

        return {
            "title": title,
            "summary": summary,
            "full_text": normalized_text,
            "ocr_text": normalized_text[:1200],
            "markers": markers[:6],
            "source": "local-pdf",
        }

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
    def _summarize_text(text: str, markers: list[dict[str, str]]) -> list[str]:
        words = text.split()
        line_one = "Report text extracted successfully."

        if markers:
            marker_names = ", ".join(marker["name"] for marker in markers[:3])
            line_two = f"Detected key report markers including {marker_names}."
        else:
            line_two = "Readable report text was found, but no standard biomarker pattern was confidently detected."

        preview = " ".join(words[:35]).strip()
        if preview:
            line_three = f"Preview: {preview[:180]}{'...' if len(preview) >= 180 else ''}"
        else:
            line_three = "The extracted text is available in the OCR tab for manual review."

        return [line_one, line_two, line_three]

    @staticmethod
    def _safe_filename(filename: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", filename or "report")
        return cleaned.strip("-") or "report"

    @staticmethod
    def _report_name(file_url: str, fallback_name: str | None = None) -> str:
        parsed_path = urlparse(file_url or "").path
        file_name = Path(parsed_path).name if parsed_path else ""
        return file_name or fallback_name or "Medical Report"

    @classmethod
    def _serialize_report(cls, report: Report) -> dict[str, Any]:
        file_name = cls._report_name(report.file_url)
        file_size = None
        parsed_path = urlparse(report.file_url or "").path.lstrip("/")
        parsed_text = (report.parsed_text or "").strip()
        if report.summary_data:
            summary_data = report.summary_data
            ocr_text = summary_data.get("ocr_text", parsed_text)
            raw_summary = summary_data.get("summary") or summary_data.get("patient_summary") or []
            summary_lines = raw_summary if isinstance(raw_summary, list) else [raw_summary]
            upload_metadata = summary_data.get("upload_metadata") if isinstance(summary_data.get("upload_metadata"), dict) else {}
            
            analysis = {
                "title": summary_data.get("title", file_name),
                "summary": summary_lines,
                "ocr_text": ocr_text,
                "markers": summary_data.get("markers") or summary_data.get("biomarkers") or [],
                "source": summary_data.get("summary_source", "prediction-service"),
            }
            summary_view = {
                "title": analysis["title"],
                "patient_info": summary_data.get("patient_info", {}),
                "key_findings": analysis["summary"],
                "biomarkers": analysis["markers"],
                "abnormal_values": summary_data.get("abnormal_values") or [],
                "notes": summary_data.get("notes", []),
                "source": analysis["source"],
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
            }
            summary_view = cls._build_summary_view("", [], [], file_name, "stored-empty")
            date_of_report = None
        if parsed_path:
            # File is now in Supabase Storage — cannot stat remote files.
            # file_size was already captured at upload time and stored by callers.
            file_size = None

        return {
            "id": str(report.id),
            "name": file_name,
            "file_name": file_name,
            "file_url": report.file_url,
            "report_type": report.report_type.value,
            "status": report.status.value,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
            "file_size": file_size,
            "parsed_text": report.parsed_text,
            "ocr_text": analysis["ocr_text"],
            "summary": analysis["summary"],
            "markers": analysis["markers"],
            "summary_source": analysis["source"],
            "summary_view": summary_view,
            "summary_data": report.summary_data or {},
            "date_of_report": date_of_report,
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
        if not normalized_text or source == "local-fallback":
            return {
                "title": title,
                "patient_info": {},
                "key_findings": [],
                "biomarkers": [],
                "abnormal_values": [],
                "notes": [],
                "source": source,
            }

        return {
            "title": title,
            "patient_info": cls._extract_patient_info(extracted_text),
            "key_findings": [line for line in summary_lines if line],
            "biomarkers": [marker for marker in markers if marker],
            "abnormal_values": [],
            "notes": cls._extract_notes(normalized_text),
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
                extracted[key] = match.group(1).strip()
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
