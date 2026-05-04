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
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from services import aqi_service
from services import dashboard_service as svc
from services.dashboard_realtime import build_dashboard_bundle

router = APIRouter(prefix="/api/v1", tags=["Dashboard"])
NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, max-age=0, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


@router.get("/dashboard")
async def get_dashboard_bundle(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    print("Serving latest dashboard data")
    bundle = await build_dashboard_bundle(db, current_user)

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": bundle,
            "last_updated": bundle.get("last_updated"),
        },
        headers=NO_CACHE_HEADERS,
    )


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


@router.get("/health/metrics")
async def get_health_metrics(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return await svc.get_health_metrics(current_user, db)


@router.get("/health/recommendation-plan")
async def get_recommendation_plan(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return await svc.get_recommendation_plan(current_user, db)


@router.get("/prediction/latest")
async def get_latest_prediction(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return await svc.get_latest_prediction(current_user, db)


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


@router.get("/health/aqi-history")
async def get_aqi_history(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    days: int = Query(7, ge=1, le=14, description="Number of days to summarize"),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Backward-compatible AQI history route for existing dashboard consumers."""
    return await aqi_service.get_aqi_history(lat, lng, days)
