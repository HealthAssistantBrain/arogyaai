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

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from services import dashboard_service as svc
from services import aqi_service
from services.user_service import UserService
from schemas.api_models import UserProfileUpdate

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
    return UserService.get_user_profile(db, current_user)


@router.put("/user/profile")
async def update_user_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return UserService.update_user_profile(
        db,
        current_user,
        payload.model_dump(exclude_unset=True),
    )


@router.get("/alerts")
async def get_alerts(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Dynamic alerts. Phase 2: populated from DB notifications table."""
    return await svc.get_alerts(current_user, db)


@router.get("/health/aqi-risk")
async def get_aqi_risk(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """
    Get Air Quality Index (AQI) data for given coordinates.
    
    Returns location name + pollutant concentrations + AQI category.
    
    Query Parameters:
        lat: Latitude (-90 to 90)
        lng: Longitude (-180 to 180)
    
    Response:
    {
        "success": bool,
        "status": "ready" | "fallback",
        "source": "openweather" | "mock",
        "data": {
            "aqi": int,
            "location": str,
            "lat": float,
            "lng": float,
            "pm25": float,
            "pm10": float,
            "no2": float,
            "o3": float,
            "so2": float,
            "category": str,
        },
        "error": str | null,
        "last_updated": ISO-8601,
    }
    """
    return await aqi_service.get_aqi_data(lat, lng)


@router.get("/health/aqi-locations")
async def get_aqi_locations(
    query: str = Query(..., min_length=2, description="City name search"),
    limit: int = Query(5, ge=1, le=8, description="Maximum suggestions"),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Return inline city suggestions for the AQI monitor search UI."""
    return await aqi_service.search_locations(query, limit)
