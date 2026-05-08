import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from services.audit_service import log_event
from services.pdf_generator import build_report_pdf_filename, generate_report_pdf_bytes
from services.report_analysis_service import analyze_report_upload
from services.report_service import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.post("/analyze")
async def analyze_report(
    file: UploadFile = File(...),
    report_type: str = Form("OTHER"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header),
):
    return await analyze_report_upload(file, db=db, current_user=current_user, report_type=report_type)


@router.post("/upload")
async def upload_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    report_type: str = Form("OTHER"),
    date_of_report: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header),
):
    try:
        result = await ReportService.upload_and_summarize(
            db,
            current_user,
            file,
            report_type,
            date_of_report=date_of_report,
            background_tasks=background_tasks,
        )
        log_event(
            current_user.id,
            "report_upload",
            "/api/v1/reports/upload",
            {
                "status": "success",
                "report_id": result.get("data", {}).get("id"),
                "file_name": file.filename,
                "file_size": result.get("data", {}).get("file_size"),
                "report_type": report_type,
                "date_of_report": result.get("data", {}).get("date_of_report"),
            },
        )
        return result
    except Exception as exc:
        log_event(
            current_user.id,
            "report_upload",
            "/api/v1/reports/upload",
            {
                "status": "failed",
                "file_name": file.filename,
                "report_type": report_type,
                "date_of_report": date_of_report,
                "error": str(exc),
            },
        )
        raise


@router.get("")
def list_reports(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header),
):
    return ReportService.list_reports(db, current_user, status_filter=status, limit=limit, offset=offset)


@router.get("/{report_id}")
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header),
):
    return ReportService.get_report(db, current_user, report_id)


@router.delete("/{report_id}")
def delete_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header),
):
    try:
        result = ReportService.delete_report(db, current_user, report_id)
        log_event(
            current_user.id,
            "report_delete",
            f"/api/v1/reports/{report_id}",
            {"status": "success", "report_id": report_id},
        )
        return result
    except Exception as exc:
        log_event(
            current_user.id,
            "report_delete",
            f"/api/v1/reports/{report_id}",
            {"status": "failed", "report_id": report_id, "error": str(exc)},
        )
        raise


@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header),
):
    report = ReportService._get_user_report(db, current_user, report_id)
    serialized = ReportService._serialize_report(report)
    pdf_bytes = generate_report_pdf_bytes(serialized)
    filename = build_report_pdf_filename(serialized)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(pdf_bytes)
        temp_path = Path(temp_file.name)

    log_event(
        current_user.id,
        "report_download",
        f"/api/v1/reports/{report_id}/download",
        {
            "status": "success",
            "report_id": report_id,
            "file_name": serialized.get("file_name"),
        },
    )

    return FileResponse(
        temp_path,
        media_type="application/pdf",
        filename=filename,
        background=BackgroundTask(lambda: temp_path.unlink(missing_ok=True)),
    )


@router.get("/{report_id}/access")
def get_report_access(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header),
):
    return ReportService.get_report_file_access(db, current_user, report_id)


@router.get("/{report_id}/status")
def get_report_status(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header),
):
    return ReportService.get_report_status(db, current_user, report_id)
