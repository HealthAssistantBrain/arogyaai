from fastapi import APIRouter, File, UploadFile

from services.report_analysis_service import analyze_report_upload

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.post("/analyze")
async def analyze_report(file: UploadFile = File(...)):
    return await analyze_report_upload(file)
