"""
aqi_service.py — Air Quality Index service

Fetches AQI data from OpenWeather API for given coordinates.
Also gets location name via reverse geocoding.

Response envelope:
{
    "success": bool,
    "status": "ready" | "fallback",
    "source": "openweather" | "mock",
    "data": {
        "aqi": int (0-500),
        "location": str,
        "lat": float,
        "lng": float,
        "pm25": float,
        "pm10": float,
        "no2": float,
        "o3": float,
        "so2": float,
        "category": str (Good/Moderate/Unhealthy etc),
        "dominant_pollutant": str,
        "aqi_method": str,
    },
    "last_updated": ISO-8601,
}
"""

import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import os
import math

logger = logging.getLogger(__name__)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENWEATHER_AQI_URL = "https://api.openweathermap.org/data/2.5/air_pollution"
OPENWEATHER_REVERSE_GEO_URL = "https://api.openweathermap.org/geo/1.0/reverse"
OPENWEATHER_DIRECT_GEO_URL = "https://api.openweathermap.org/geo/1.0/direct"


def _now() -> str:
    """ISO-8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _envelope(data: dict, status: str, source: str, error: Optional[str] = None) -> dict:
    """Standard response envelope."""
    return {
        "success": error is None,
        "status": status,  # "ready" | "fallback"
        "source": source,  # "openweather" | "mock"
        "data": data,
        "error": error,
        "last_updated": _now(),
    }


def _get_aqi_category(aqi_index: int) -> str:
    """Convert AQI index to category."""
    if aqi_index <= 50:
        return "Good"
    elif aqi_index <= 100:
        return "Moderate"
    elif aqi_index <= 150:
        return "Unhealthy (S)"
    elif aqi_index <= 200:
        return "Unhealthy"
    elif aqi_index <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"


def _truncate(value: float, digits: int) -> float:
    """Truncate without rounding to align with AQI breakpoint guidance."""
    factor = 10 ** digits
    return math.floor(value * factor) / factor


def _calculate_sub_index(
    concentration: float,
    breakpoints: list[tuple[float, float, int, int]],
    truncate_digits: int,
) -> Optional[int]:
    """Calculate AQI sub-index from pollutant concentration."""
    normalized = _truncate(concentration, truncate_digits)

    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= normalized <= c_high:
            sub_index = ((i_high - i_low) / (c_high - c_low)) * (normalized - c_low) + i_low
            return round(sub_index)

    if normalized > breakpoints[-1][1]:
        return 500

    return None


def _calculate_aqi_from_pollutants(pm25: float, pm10: float) -> int:
    """
    Approximate AQI on a 0-500 scale using particulate matter concentrations.

    OpenWeather provides current pollutant concentrations in µg/m³. We compute
    PM2.5 and PM10 AQI sub-indices using standard EPA breakpoint interpolation
    and take the higher one as the displayed AQI.
    """
    pm25_breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]
    pm10_breakpoints = [
        (0.0, 54.0, 0, 50),
        (55.0, 154.0, 51, 100),
        (155.0, 254.0, 101, 150),
        (255.0, 354.0, 151, 200),
        (355.0, 424.0, 201, 300),
        (425.0, 504.0, 301, 400),
        (505.0, 604.0, 401, 500),
    ]

    sub_indices = [
        _calculate_sub_index(pm25, pm25_breakpoints, 1),
        _calculate_sub_index(pm10, pm10_breakpoints, 0),
    ]
    valid_indices = [index for index in sub_indices if index is not None]
    return max(valid_indices, default=50)


def _get_dominant_pollutant(pm25: float, pm10: float) -> str:
    """Identify which particulate pollutant is driving the AQI."""
    pm25_breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]
    pm10_breakpoints = [
        (0.0, 54.0, 0, 50),
        (55.0, 154.0, 51, 100),
        (155.0, 254.0, 101, 150),
        (255.0, 354.0, 151, 200),
        (355.0, 424.0, 201, 300),
        (425.0, 504.0, 301, 400),
        (505.0, 604.0, 401, 500),
    ]

    pm25_index = _calculate_sub_index(pm25, pm25_breakpoints, 1) or 0
    pm10_index = _calculate_sub_index(pm10, pm10_breakpoints, 0) or 0

    return "PM2.5" if pm25_index >= pm10_index else "PM10"


async def _fetch_location_name(lat: float, lng: float) -> str:
    """
    Reverse geocode lat/lng to get location name.
    Falls back to "Unknown Location" if API fails.
    """
    if not OPENWEATHER_API_KEY:
        return f"Lat: {lat:.2f}, Lng: {lng:.2f}"
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                OPENWEATHER_REVERSE_GEO_URL,
                params={
                    "lat": lat,
                    "lon": lng,
                    "limit": 1,
                    "appid": OPENWEATHER_API_KEY,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    loc = data[0]
                    city = loc.get("name", "")
                    state = loc.get("state", "")
                    country = loc.get("country", "")
                    
                    parts = [p for p in [city, state, country] if p]
                    return ", ".join(parts) if parts else f"Lat: {lat:.2f}, Lng: {lng:.2f}"
                    
    except Exception as e:
        logger.warning(f"[AQI Service] Reverse geocoding failed: {str(e)}")
    
    return f"Lat: {lat:.2f}, Lng: {lng:.2f}"


async def search_locations(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Search city suggestions using OpenWeather direct geocoding.

    Returns a small normalized list the frontend can render directly.
    """
    normalized_query = query.strip()
    capped_limit = max(1, min(limit, 8))

    if len(normalized_query) < 2:
        return _envelope(
            data={"query": normalized_query, "suggestions": []},
            status="ready",
            source="mock" if not OPENWEATHER_API_KEY else "openweather",
        )

    if not OPENWEATHER_API_KEY:
        logger.error("[AQI Service] OPENWEATHER_API_KEY not configured for city search")
        return _envelope(
            data={"query": normalized_query, "suggestions": []},
            status="fallback",
            source="mock",
            error="API key not configured",
        )

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                OPENWEATHER_DIRECT_GEO_URL,
                params={
                    "q": normalized_query,
                    "limit": capped_limit,
                    "appid": OPENWEATHER_API_KEY,
                }
            )

        if response.status_code != 200:
            logger.error(f"[AQI Service] City search API error: {response.status_code}")
            return _envelope(
                data={"query": normalized_query, "suggestions": []},
                status="fallback",
                source="mock",
                error=f"OpenWeather API returned {response.status_code}",
            )

        raw_locations = response.json() or []
        suggestions = []
        seen_keys = set()

        for item in raw_locations:
            city = item.get("name", "").strip()
            state = item.get("state", "").strip()
            country = item.get("country", "").strip()
            lat = item.get("lat")
            lng = item.get("lon")

            if not city or lat is None or lng is None:
                continue

            key = (city.lower(), state.lower(), country.lower(), round(lat, 4), round(lng, 4))
            if key in seen_keys:
                continue
            seen_keys.add(key)

            parts = [part for part in [city, state, country] if part]
            suggestions.append({
                "name": city,
                "state": state,
                "country": country,
                "label": ", ".join(parts),
                "lat": round(float(lat), 6),
                "lng": round(float(lng), 6),
            })

        return _envelope(
            data={"query": normalized_query, "suggestions": suggestions},
            status="ready",
            source="openweather",
        )

    except httpx.RequestError as e:
        logger.error(f"[AQI Service] City search network error: {str(e)}")
        return _envelope(
            data={"query": normalized_query, "suggestions": []},
            status="fallback",
            source="mock",
            error=str(e),
        )
    except Exception as e:
        logger.error(f"[AQI Service] City search unexpected error: {str(e)}")
        return _envelope(
            data={"query": normalized_query, "suggestions": []},
            status="fallback",
            source="mock",
            error="Failed to search cities",
        )


async def get_aqi_data(lat: float, lng: float) -> Dict[str, Any]:
    """
    Fetch AQI data from OpenWeather API.
    
    Args:
        lat: Latitude (-90 to 90)
        lng: Longitude (-180 to 180)
    
    Returns:
        Standard envelope dict
    """
    
    if not OPENWEATHER_API_KEY:
        logger.error("[AQI Service] OPENWEATHER_API_KEY not configured")
        return _envelope(
            data={
                "aqi": 50,
                "location": "Default Location",
                "lat": lat,
                "lng": lng,
                "pm25": 15.0,
                "pm10": 25.0,
                "no2": 20.0,
                "o3": 50.0,
                "so2": 10.0,
                "category": "Good",
                "dominant_pollutant": "PM2.5",
                "aqi_method": "fallback_mock",
            },
            status="fallback",
            source="mock",
            error="API key not configured",
        )
    
    try:
        # Fetch AQI data
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(
                OPENWEATHER_AQI_URL,
                params={
                    "lat": lat,
                    "lon": lng,
                    "appid": OPENWEATHER_API_KEY,
                }
            )
            
            if response.status_code != 200:
                logger.error(f"[AQI Service] OpenWeather API error: {response.status_code}")
                return _envelope(
                    data={
                        "aqi": 50,
                        "location": await _fetch_location_name(lat, lng),
                        "lat": lat,
                        "lng": lng,
                        "pm25": 15.0,
                        "pm10": 25.0,
                        "no2": 20.0,
                        "o3": 50.0,
                        "so2": 10.0,
                        "category": "Good",
                        "dominant_pollutant": "PM2.5",
                        "aqi_method": "fallback_mock",
                    },
                    status="fallback",
                    source="mock",
                    error=f"OpenWeather API returned {response.status_code}",
                )
            
            api_data = response.json()
            readings = api_data.get("list", [])
            current_reading = readings[0] if readings else {}

            # OpenWeather nests AQI + pollutants inside list[0]
            components = current_reading.get("components", {})
            # Extract pollutant concentrations
            pm25 = components.get("pm2_5", 12.5)
            pm10 = components.get("pm10", 22.5)
            no2 = components.get("no2", 20.0)
            o3 = components.get("o3", 50.0)
            so2 = components.get("so2", 10.0)
            aqi_standard = _calculate_aqi_from_pollutants(pm25, pm10)
            dominant_pollutant = _get_dominant_pollutant(pm25, pm10)
            
            # Get location name
            location_name = await _fetch_location_name(lat, lng)
            
            return _envelope(
                data={
                    "aqi": int(aqi_standard),
                    "location": location_name,
                    "lat": lat,
                    "lng": lng,
                    "pm25": round(pm25, 2),
                    "pm10": round(pm10, 2),
                    "no2": round(no2, 2),
                    "o3": round(o3, 2),
                    "so2": round(so2, 2),
                    "category": _get_aqi_category(int(aqi_standard)),
                    "dominant_pollutant": dominant_pollutant,
                    "aqi_method": "openweather_pm_epa_interp",
                },
                status="ready",
                source="openweather",
            )
    
    except httpx.RequestError as e:
        logger.error(f"[AQI Service] Network error: {str(e)}")
        # Fallback with mock data
        location_name = await _fetch_location_name(lat, lng)
        return _envelope(
            data={
                "aqi": 50,
                "location": location_name,
                "lat": lat,
                "lng": lng,
                "pm25": 15.0,
                "pm10": 25.0,
                "no2": 20.0,
                "o3": 50.0,
                "so2": 10.0,
                "category": "Good",
                "dominant_pollutant": "PM2.5",
                "aqi_method": "fallback_mock",
            },
            status="fallback",
            source="mock",
            error=str(e),
        )
    
    except Exception as e:
        logger.error(f"[AQI Service] Unexpected error: {str(e)}")
        return _envelope(
            data={
                "aqi": 50,
                "location": "Error retrieving location",
                "lat": lat,
                "lng": lng,
                "pm25": 15.0,
                "pm10": 25.0,
                "no2": 20.0,
                "o3": 50.0,
                "so2": 10.0,
                "category": "Good",
                "dominant_pollutant": "PM2.5",
                "aqi_method": "fallback_mock",
            },
            status="fallback",
            source="mock",
            error="Failed to fetch AQI data",
        )
