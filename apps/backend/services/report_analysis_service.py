from __future__ import annotations

from io import BytesIO
from uuid import uuid4

from PyPDF2 import PdfReader
from fastapi import HTTPException, UploadFile

from integrations.prediction_client import PredictionClient

import logging

logger = logging.getLogger("uvicorn.error")
prediction_client = PredictionClient()


async def analyze_report_upload(file: UploadFile) -> dict:
    if not _is_supported_pdf(file):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()
    request_id = str(uuid4())
    logger.warning(
        "Medical report received: request_id=%s name=%s content_type=%s size=%s",
        request_id,
        file.filename,
        file.content_type,
        len(file_bytes),
    )

    extracted_text = _extract_text_from_pdf(file_bytes)
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

    return {
        "success": True,
        "status": "ready",
        "source": "report-analysis",
        "error": None,
        "data": {
            "request_id": request_id,
            "report_id": str(uuid4()),
            "file_name": file.filename,
            "pipeline": {
                "upload": "completed",
                "text_extraction": "completed",
                "prediction": "completed",
                "insights": "completed",
            },
            "summary": prediction_data.get("summary") or prediction_data.get("patient_summary") or "Analysis complete.",
            "patient_summary": prediction_data.get("patient_summary") or prediction_data.get("summary") or "Analysis complete.",
            "risks": prediction_data.get("risks") or [],
            "risk_level": prediction_data.get("risk_level") or _derive_risk_level(prediction_data.get("risks") or []),
            "recommendations": prediction_data.get("recommendations") or [],
            "abnormal_values": prediction_data.get("abnormal_values") or [],
            "extracted_text_length": len(extracted_text),
        },
    }


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(page.strip() for page in pages if page and page.strip())
    except Exception as exc:
        logger.exception("PDF text extraction failed")
        raise HTTPException(status_code=500, detail="Failed to extract text from the uploaded PDF.") from exc


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
