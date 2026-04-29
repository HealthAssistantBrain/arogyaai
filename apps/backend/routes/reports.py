from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from services.audit_service import log_event
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header),
):
    try:
        result = await ReportService.upload_and_summarize(
            db,
            current_user,
            file,
            report_type,
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
