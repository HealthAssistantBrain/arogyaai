from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.session import get_db
from routes.users import get_current_user_from_header
from services.google_fit_service import GoogleFitService

router = APIRouter(prefix="/api/v1/vitals", tags=["Vitals"])


@router.get("/heart-rate")
async def get_heart_rate(
    timezone: str | None = Query(default=None),
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    payload = await GoogleFitService.sync_heart_rate(
        db,
        current_user,
        timezone_name=timezone,
    )

    return {
        "success": True,
        "status": "success",
        "message": payload["message"],
        "connected": payload["connected"],
        "data": payload["data"],
    }
