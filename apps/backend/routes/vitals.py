from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from services.google_fit_service import GoogleFitService
from services.user_data_service import UserDataService

router = APIRouter(prefix="/api/v1/vitals", tags=["Vitals"])


@router.get("")
def get_vitals(
    type: str | None = Query(default=None),
    range: str = Query(default="24h"),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return UserDataService.list_vitals(db, current_user, vital_type=type, range_value=range)


@router.get("/heart-rate")
def get_heart_rate(
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    payload = UserDataService.list_vitals(db, current_user, vital_type="heart_rate", range_value="24h")
    connection_status = GoogleFitService.get_status(db, current_user)
    return {
        "success": True,
        "status": "ready",
        "message": None if payload["data"]["vitals"] else "No heart rate data available",
        "connected": bool(connection_status.get("connected")),
        "data": payload["data"]["vitals"],
    }
