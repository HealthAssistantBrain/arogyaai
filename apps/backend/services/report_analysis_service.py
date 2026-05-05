from __future__ import annotations

from uuid import uuid4
import logging
from typing import Any

from fastapi import HTTPException, UploadFile

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from integrations.prediction_client import PredictionClient
from integrations.ocr_service import OCRInput, OCRService
from models import Report, ReportStatusEnum, ReportTypeEnum, User
from services.report_service import ReportService
from services.timeline_service import create_report_timeline_event

logger = logging.getLogger("uvicorn.error")
prediction_client = PredictionClient()


async def analyze_report_upload(
    file: UploadFile,
    db: Session | None = None,
    current_user: User | None = None,
    report_type: str | None = None,
) -> dict[str, Any]:
    if not _is_supported_pdf(file):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()
    if db is not None and current_user is not None:
        file_hash = ReportService._compute_file_hash(file_bytes)
        existing_report = ReportService._get_report_by_hash(db, current_user.id, file_hash)
        if existing_report:
            logger.info(
                "REPORT_DUPLICATE_SKIPPED user_id=%s report_id=%s file_hash=%s status=%s",
                current_user.id,
                existing_report.id,
                file_hash,
                existing_report.status.value,
            )
            serialized = ReportService._serialize_report(existing_report)
            return {
                "success": True,
                "status": "ready",
                "source": "report-analysis",
                "error": None,
                "data": {
                    **serialized,
                    "request_id": str(uuid4()),
                    "report_id": serialized["id"],
                    "pipeline": {
                        "upload": "completed",
                        "text_extraction": "completed",
                        "prediction": "completed",
                        "insights": "completed",
                    },
                    "extracted_text_length": len(serialized.get("parsed_text") or serialized.get("ocr_text") or ""),
                },
            }
    request_id = str(uuid4())
    logger.warning(
        "Medical report received: request_id=%s name=%s content_type=%s size=%s",
        request_id,
        file.filename,
        file.content_type,
        len(file_bytes),
    )

    extracted_text, text_source, ocr_confidence, text_pages = _extract_text_from_pdf(file_bytes, file.filename or "report.pdf")
    print("Extracted text length:", len(extracted_text or ""))
    logger.warning(
        "Medical report text extracted: request_id=%s name=%s chars=%s preview=%s",
        request_id,
        file.filename,
        len(extracted_text),
        extracted_text[:160].replace("\n", " "),
    )

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="No readable text was found in the uploaded PDF.")

    payload = {
        "file_name": file.filename,
        "extracted_text": extracted_text,
    }
    logger.warning(
        "Sending prediction request: request_id=%s file=%s url=%s",
        request_id,
        file.filename,
        f"{prediction_client.base_url}/predict",
    )
    prediction_response = await prediction_client.get_prediction(payload)
    logger.warning(
        "Prediction response received: request_id=%s file=%s success=%s status=%s",
        request_id,
        file.filename,
        prediction_response.get("success"),
        prediction_response.get("status"),
    )

    if not prediction_response.get("success") or prediction_response.get("status") != "ready":
        raise HTTPException(
            status_code=502,
            detail=prediction_response.get("error") or "Prediction service failed to process the report.",
        )

    prediction_data = prediction_response.get("data") or {}
    persisted_report = None
    fallback_report_id = str(uuid4())

    if db is not None and current_user is not None:
        persisted_report = _persist_analyzed_report(
            db=db,
            current_user=current_user,
            file=file,
            file_bytes=file_bytes,
            report_type=report_type or "OTHER",
            prediction_data=prediction_data,
            extracted_text=extracted_text,
            text_source=text_source,
            ocr_confidence=ocr_confidence,
            text_pages=text_pages,
        )

    structured_summary = ReportService._normalize_structured_summary(
        prediction_data.get("structured_summary") or prediction_data.get("summary"),
        fallback_title=file.filename or "Medical Report",
        fallback_summary=prediction_data.get("patient_summary") or prediction_data.get("summary") or "Analysis complete.",
    )
    summary_view = ReportService._summary_view_from_structured_summary(
        structured_summary,
        source=prediction_data.get("summary_source") or "prediction-service",
        stored_view=prediction_data.get("summary_view") if isinstance(prediction_data.get("summary_view"), dict) else {},
    )
    patient_summary = prediction_data.get("patient_summary") or " ".join(
        ReportService._summary_lines(structured_summary)
    ) or "Analysis complete."

    response_data = {
        "request_id": request_id,
        "report_id": persisted_report["id"] if persisted_report else fallback_report_id,
        "id": persisted_report["id"] if persisted_report else fallback_report_id,
        "name": persisted_report["name"] if persisted_report else file.filename,
        "file_name": persisted_report["file_name"] if persisted_report else file.filename,
        "file_url": persisted_report["file_url"] if persisted_report else None,
        "file_size": len(file_bytes),
        "report_type": persisted_report["report_type"] if persisted_report else (report_type or "OTHER"),
        "status": persisted_report["status"] if persisted_report else "COMPLETED",
        "created_at": persisted_report["created_at"] if persisted_report else None,
        "updated_at": persisted_report["updated_at"] if persisted_report else None,
        "pipeline": {
            "upload": "completed",
            "text_extraction": "completed",
            "prediction": "completed",
            "insights": "completed",
        },
        "summary": structured_summary,
        "structured_summary": structured_summary,
        "summary_view": summary_view,
        "patient_summary": patient_summary,
        "risks": prediction_data.get("risks") or [],
        "risk_level": prediction_data.get("risk_level") or _derive_risk_level(prediction_data.get("risks") or []),
        "recommendations": prediction_data.get("recommendations") or [],
        "abnormal_values": prediction_data.get("abnormal_values") or [],
        "extracted_text_length": len(extracted_text),
        "ocr_text": extracted_text,
        "summary_source": prediction_data.get("summary_source") or "prediction-service",
        "text_source": text_source,
        "ocr_confidence": ocr_confidence,
        "text_pages": text_pages,
    }

    return {
        "success": True,
        "status": "ready",
        "source": "report-analysis",
        "error": None,
        "data": response_data,
    }


def _extract_text_from_pdf(file_bytes: bytes, filename: str = "report.pdf") -> tuple[str, str, float | None, list[dict[str, Any]]]:
    pdf_pages: list[dict[str, Any]] = []
    try:
        pdf_pages = ReportService._extract_pdf_pages(file_bytes)
    except Exception as exc:
        logger.info("PDF text extraction unavailable; continuing with OCR: %s", exc)

    ocr_result = OCRService().extract_text(
        OCRInput(filename=filename, content=file_bytes, content_type="application/pdf")
    )
    extracted_text, text_pages, text_source = ReportService._merge_pdf_and_ocr_text(pdf_pages, ocr_result)
    return extracted_text, text_source, ocr_result.confidence, text_pages


def _is_supported_pdf(file: UploadFile) -> bool:
    content_type = (file.content_type or "").lower()
    file_name = (file.filename or "").lower()
    return content_type == "application/pdf" or file_name.endswith(".pdf")


def _derive_risk_level(risks: list[str]) -> str:
    if len(risks) >= 2:
        return "Moderate"
    if risks:
        return "Low"
    return "Low"


def _coerce_report_type(report_type: str | None, file_name: str) -> ReportTypeEnum:
    normalized = (report_type or "").strip().upper()
    if normalized:
        try:
            return ReportTypeEnum(normalized)
        except ValueError:
            pass

    extension = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
    if extension == "pdf":
        return ReportTypeEnum.BLOOD_TEST
    if extension in {"jpg", "jpeg"}:
        return ReportTypeEnum.XRAY
    if extension == "png":
        return ReportTypeEnum.CLINICAL_NOTE

    return ReportTypeEnum.OTHER


def _persist_analyzed_report(
    db: Session,
    current_user: User,
    file: UploadFile,
    file_bytes: bytes,
    report_type: str,
    prediction_data: dict[str, Any],
    extracted_text: str,
    text_source: str,
    ocr_confidence: float | None,
    text_pages: list[dict[str, Any]],
) -> dict[str, Any]:
    original_filename = file.filename or "report.pdf"
    file_hash = ReportService._compute_file_hash(file_bytes)
    existing_report = ReportService._get_report_by_hash(db, current_user.id, file_hash)
    if existing_report:
        logger.info(
            "REPORT_DUPLICATE_SKIPPED user_id=%s report_id=%s file_hash=%s status=%s",
            current_user.id,
            existing_report.id,
            file_hash,
            existing_report.status.value,
        )
        serialized = ReportService._serialize_report(existing_report)
        return {
            "id": serialized["id"],
            "name": serialized["name"],
            "file_name": serialized["file_name"],
            "original_filename": serialized["original_filename"],
            "stored_filename": serialized["stored_filename"],
            "file_url": serialized["file_url"],
            "file_size": serialized["file_size"],
            "report_type": serialized["report_type"],
            "status": serialized["status"],
            "created_at": serialized["created_at"],
            "updated_at": serialized["updated_at"],
            "storage_path": serialized["storage_path"],
            "summary_source": serialized["summary_source"],
        }

    storage_path, public_url = ReportService._persist_file(current_user.id, original_filename, file_bytes)
    stored_filename = ReportService._stored_filename(storage_path, public_url)
    normalized_type = _coerce_report_type(report_type, original_filename)
    structured_summary = ReportService._normalize_structured_summary(
        prediction_data.get("structured_summary") or prediction_data.get("summary"),
        fallback_title=original_filename,
        fallback_summary=prediction_data.get("patient_summary") or prediction_data.get("summary") or "Analysis complete.",
    )
    summary_view = ReportService._summary_view_from_structured_summary(
        structured_summary,
        source=prediction_data.get("summary_source") or "prediction-service",
        stored_view=prediction_data.get("summary_view") if isinstance(prediction_data.get("summary_view"), dict) else {},
    )
    patient_summary = prediction_data.get("patient_summary") or " ".join(
        ReportService._summary_lines(structured_summary)
    ) or "Analysis complete."

    report = Report(
        user_id=current_user.id,
        report_type=normalized_type,
        file_url=public_url,
        file_hash=file_hash,
        original_filename=original_filename,
        stored_filename=stored_filename,
        parsed_text=extracted_text,
        summary_data={
            "upload_metadata": ReportService._upload_metadata(
                original_filename=original_filename,
                stored_filename=stored_filename,
                storage_path=str(storage_path),
                file_size=len(file_bytes),
                file_hash=file_hash,
            ),
            "full_text": extracted_text,
            "ocr_text": extracted_text[:1200],
            "text_source": text_source,
            "ocr_confidence": ocr_confidence,
            "text_pages": text_pages,
            "summary": structured_summary,
            "structured_summary": structured_summary,
            "summary_view": summary_view,
            "patient_summary": patient_summary,
            "risks": prediction_data.get("risks") or [],
            "risk_level": prediction_data.get("risk_level") or _derive_risk_level(prediction_data.get("risks") or []),
            "recommendations": prediction_data.get("recommendations") or [],
            "abnormal_values": prediction_data.get("abnormal_values") or [],
            "summary_source": prediction_data.get("summary_source") or "prediction-service",
        },
        status=ReportStatusEnum.COMPLETED,
    )
    db.add(report)
    try:
        db.flush()
        create_report_timeline_event(db, report, commit=False)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_report = ReportService._get_report_by_hash(db, current_user.id, file_hash)
        if existing_report:
            logger.info(
                "REPORT_DUPLICATE_SKIPPED user_id=%s report_id=%s file_hash=%s status=%s",
                current_user.id,
                existing_report.id,
                file_hash,
                existing_report.status.value,
            )
            serialized = ReportService._serialize_report(existing_report)
            return {
                "id": serialized["id"],
                "name": serialized["name"],
                "file_name": serialized["file_name"],
                "original_filename": serialized["original_filename"],
                "stored_filename": serialized["stored_filename"],
                "file_url": serialized["file_url"],
                "file_size": serialized["file_size"],
                "report_type": serialized["report_type"],
                "status": serialized["status"],
                "created_at": serialized["created_at"],
                "updated_at": serialized["updated_at"],
                "storage_path": serialized["storage_path"],
                "summary_source": serialized["summary_source"],
            }
        raise
    db.refresh(report)
    logger.info(
        "REPORT_CREATED user_id=%s report_id=%s file_hash=%s status=%s",
        current_user.id,
        report.id,
        file_hash,
        report.status.value,
    )

    # ── Lab pipeline hook (non-fatal) ──────────────────────────────────────
    # Runs after the report is committed so report.id exists in the DB.
    try:
        from services.lab_pipeline_service import run_lab_pipeline
        run_lab_pipeline(
            text=extracted_text,
            user_id=current_user.id,
            report_id=report.id,
            db=db,
            source_type=text_source,
            source_confidence=ocr_confidence,
            page_metadata=text_pages,
        )
    except Exception:
        logger.exception(
            "Lab pipeline failed — lab results not persisted for report %s", report.id
        )
    # ── end lab pipeline hook ──────────────────────────────────────────────

    return {
        "id": str(report.id),
        "name": original_filename,
        "file_name": original_filename,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "file_url": report.file_url,
        "file_size": len(file_bytes),
        "report_type": report.report_type.value,
        "status": report.status.value,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
        "storage_path": str(storage_path),
        "summary_source": prediction_data.get("summary_source") or "prediction-service",
    }
