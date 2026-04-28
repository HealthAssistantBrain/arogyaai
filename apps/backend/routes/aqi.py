from fastapi import APIRouter, Depends, Query

from models import User
from routes.users import get_current_user_from_header
from services import aqi_service

router = APIRouter(prefix="/api/v1", tags=["AQI"])


@router.get("/aqi")
async def get_aqi(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    current_user: User = Depends(get_current_user_from_header),
):
    return await aqi_service.get_aqi_data(lat, lng)


@router.get("/aqi/history")
async def get_aqi_history(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    days: int = Query(7, ge=1, le=14, description="Number of days to summarize"),
    current_user: User = Depends(get_current_user_from_header),
):
    return await aqi_service.get_aqi_history(lat, lng, days)


@router.get("/geocode")
async def geocode_locations(
    q: str = Query(..., min_length=2, description="Location query"),
    limit: int = Query(5, ge=1, le=8, description="Maximum suggestions"),
    current_user: User = Depends(get_current_user_from_header),
):
    return await aqi_service.search_locations(q, limit)
