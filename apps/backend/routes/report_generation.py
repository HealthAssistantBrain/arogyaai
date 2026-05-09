import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.report_generation import ReportGenerationRequest
from services.report_generation import ReportGenerationService

router = APIRouter(prefix="/api/v1/report-generation", tags=["Report Generation"])


@router.post("/generate")
def generate_report(
    payload: ReportGenerationRequest,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    data = ReportGenerationService.generate(db, current_user, payload)
    return {
        "success": True,
        "status": "ready",
        "source": "db+report_generation",
        "error": None,
        "data": data,
    }


@router.get("/history")
def get_generated_report_history(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    data = ReportGenerationService.history(db, current_user, limit=limit)
    return {
        "success": True,
        "status": "ready" if data else "empty",
        "source": "db",
        "error": None,
        "data": data,
    }


@router.get("/{report_id}")
def get_generated_report(
    report_id: str,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    data = ReportGenerationService.get_one(db, current_user, report_id)
    return {
        "success": True,
        "status": "ready",
        "source": "db",
        "error": None,
        "data": data,
    }


@router.get("/{report_id}/export")
def export_generated_report_pdf(
    report_id: str,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    pdf_bytes, filename = ReportGenerationService.export_pdf_bytes(db, current_user, report_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(pdf_bytes)
        temp_path = Path(temp_file.name)

    return FileResponse(
        temp_path,
        media_type="application/pdf",
        filename=filename,
        background=BackgroundTask(lambda: temp_path.unlink(missing_ok=True)),
    )
