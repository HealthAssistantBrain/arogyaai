from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from services.google_fit_service import GoogleFitService
from services.user_data_service import UserDataService

router = APIRouter(prefix="/api/v1/vitals", tags=["Vitals"])


def _serialize_vitals_response(payload: dict, vital_type: str | None, range_value: str) -> dict:
    vitals = payload.get("data", {}).get("vitals", []) if isinstance(payload, dict) else []
    trimmed = vitals[-100:] if len(vitals) > 100 else vitals
    data = [
        {
            "value": item.get("value"),
            "timestamp": item.get("timestamp"),
            "unit": item.get("unit"),
            "type": item.get("type"),
            "source": item.get("source"),
        }
        for item in trimmed
    ]
    return {
        "type": vital_type,
        "range": range_value,
        "data": data,
        "total_count": len(data),
        "last_updated": payload.get("last_updated") if isinstance(payload, dict) else None,
    }


@router.get("")
def get_vitals(
    type: str | None = Query(default=None),
    range: str = Query(default="24h"),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    payload = UserDataService.list_vitals(db, current_user, vital_type=type, range_value=range)
    return _serialize_vitals_response(payload, type, range)


@router.get("/heart-rate")
def get_heart_rate(
    current_user=Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    payload = UserDataService.list_vitals(db, current_user, vital_type="heart_rate", range_value="24h")
    return {
        "success": True,
        "status": "ready",
        "message": None if payload["data"]["vitals"] else "No heart rate data available",
        "connected": bool(GoogleFitService.get_status(db, current_user).get("connected")),
        "data": _serialize_vitals_response(payload, "heart_rate", "24h")["data"],
    }
