import mimetypes
import re
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy.orm import Session

from models import Report, ReportStatusEnum, ReportTypeEnum, User


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
    ) -> dict[str, Any]:
        cls._validate_report_type(report_type)
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

        storage_path, public_url = cls._persist_file(current_user.id, file.filename, file_bytes)

        report = Report(
            user_id=current_user.id,
            report_type=ReportTypeEnum(report_type),
            file_url=public_url,
            status=ReportStatusEnum.PROCESSING,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        try:
            analysis = await cls._analyze_report(file.filename or "report", file.content_type, file_bytes)
            report.parsed_text = analysis["ocr_text"]
            report.status = ReportStatusEnum.COMPLETED
            db.commit()
            db.refresh(report)
        except Exception as exc:
            report.status = ReportStatusEnum.FAILED
            db.commit()
            db.refresh(report)
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
            },
        }

    @classmethod
    def _persist_file(cls, user_id: Any, original_name: str, file_bytes: bytes) -> tuple[Path, str]:
        safe_name = cls._safe_filename(original_name)
        user_dir = Path(settings.REPORT_UPLOAD_DIR) / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        storage_path = user_dir / f"{uuid.uuid4()}-{safe_name}"
        storage_path.write_bytes(file_bytes)

        relative_path = storage_path.as_posix().lstrip("./")
        public_url = f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/{relative_path}"
        return storage_path, public_url

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
            "ocr_text": "Image OCR is not configured on this machine yet.",
            "markers": [],
            "source": "local-fallback",
        }

    @staticmethod
    def _extract_pdf_text(file_bytes: bytes) -> str:
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
                "ocr_text": "No text could be extracted from this PDF.",
                "markers": [],
                "source": "local-fallback",
            }

        markers = cls._extract_markers(normalized_text)
        summary = cls._summarize_text(normalized_text, markers)

        return {
            "title": title,
            "summary": summary,
            "ocr_text": normalized_text[:1200],
            "markers": markers[:6],
            "source": "local-pdf",
        }

    @staticmethod
    def _extract_markers(text: str) -> list[dict[str, str]]:
        marker_patterns = [
            ("Hemoglobin", r"hemoglobin[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(g/dl|gm/dl|g%)?"),
            ("WBC", r"(?:wbc|white blood cells?)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(?:/mm3|cells/?u?l|10\^3/?u?l)?"),
            ("RBC", r"(?:rbc|red blood cells?)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(?:million/?u?l|10\^6/?u?l)?"),
            ("Platelets", r"(?:platelets?)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(?:lakhs/?cumm|10\^3/?u?l|/mm3)?"),
            ("Glucose", r"(?:glucose|blood sugar|fasting glucose)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(mg/dl)?"),
            ("HbA1c", r"(?:hba1c|a1c)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(%)?"),
            ("Creatinine", r"(?:creatinine)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(mg/dl)?"),
            ("Urea", r"(?:urea|blood urea)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(mg/dl)?"),
            ("TSH", r"(?:tsh)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(uIU/ml|miu/l|mIU/L)?"),
            ("Vitamin D", r"(?:vitamin d|25-oh vitamin d)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(ng/ml)?"),
            ("Cholesterol", r"(?:total cholesterol|cholesterol)[:\s\-]*([0-9]+(?:\.[0-9]+)?)\s*(mg/dl)?"),
        ]

        markers = []
        lowered = text.lower()
        for name, pattern in marker_patterns:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if not match:
                continue
            markers.append(
                {
                    "name": name,
                    "value": match.group(1) or "",
                    "unit": (match.group(2) or "").strip(),
                    "flag": "captured",
                }
            )
        return markers

    @staticmethod
    def _summarize_text(text: str, markers: list[dict[str, str]]) -> list[str]:
        words = text.split()
        line_one = "PDF report uploaded and text extracted successfully."

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
    def _validate_report_type(report_type: str) -> None:
        allowed = {item.value for item in ReportTypeEnum}
        if report_type not in allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report type.")
