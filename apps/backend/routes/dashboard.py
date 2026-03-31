"""
dashboard.py — Dashboard route handlers (thin layer)

All business logic lives in services/dashboard_service.py.
These handlers only handle auth + HTTP concerns.

Pipeline-compatible response envelope:
    {
        "success":      bool,
        "status":       "ready" | "processing" | "fallback",
        "source":       "ml" | "wearable" | "computed" | "mock",
        "data":         {...},
        "last_updated": ISO-8601,
    }
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from services import dashboard_service as svc

router = APIRouter(prefix="/api/v1", tags=["Dashboard"])


@router.get("/health/score")
async def get_health_score(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return await svc.get_health_score(current_user, db)


@router.get("/health/history")
async def get_health_history(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return await svc.get_health_history(current_user, db)


@router.get("/prediction/latest")
async def get_latest_prediction(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return await svc.get_latest_prediction(current_user, db)


@router.get("/user/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return await svc.get_user_profile(current_user, db)


@router.get("/alerts")
async def get_alerts(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Dynamic alerts. Phase 2: populated from DB notifications table."""
    return await svc.get_alerts(current_user, db)
