<<<<<<< HEAD
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from services.report_service import ReportService
=======
from fastapi import APIRouter, File, UploadFile

from services.report_analysis_service import analyze_report_upload
>>>>>>> Report_Gen

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


<<<<<<< HEAD
@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_report(
    file: UploadFile = File(...),
    report_type: str = Form(...),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return await ReportService.upload_and_summarize(
        db=db,
        current_user=current_user,
        file=file,
        report_type=report_type,
    )
=======
@router.post("/analyze")
async def analyze_report(file: UploadFile = File(...)):
    return await analyze_report_upload(file)
>>>>>>> Report_Gen
