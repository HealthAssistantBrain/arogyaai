"""
aqi_service.py — Air Quality Index service

Fetches current AQI, location search, and 7-day pollutant history from the
OpenWeather APIs and normalizes the payloads for the AQI monitor frontend.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import math
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENWEATHER_AQI_URL = "https://api.openweathermap.org/data/2.5/air_pollution"
OPENWEATHER_HISTORY_URL = "https://api.openweathermap.org/data/2.5/air_pollution/history"
OPENWEATHER_REVERSE_GEO_URL = "https://api.openweathermap.org/geo/1.0/reverse"
OPENWEATHER_DIRECT_GEO_URL = "https://api.openweathermap.org/geo/1.0/direct"
DEFAULT_HISTORY_DAYS = 7


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _envelope(data: dict, status: str, source: str, error: Optional[str] = None) -> dict:
    return {
        "success": error is None,
        "status": status,
        "source": source,
        "data": data,
        "error": error,
        "last_updated": _now(),
    }


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_aqi_category(aqi_index: int) -> str:
    if aqi_index <= 50:
        return "Good"
    if aqi_index <= 100:
        return "Moderate"
    if aqi_index <= 150:
        return "Unhealthy (Sensitive)"
    if aqi_index <= 200:
        return "Unhealthy"
    if aqi_index <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def _truncate(value: float, digits: int) -> float:
    factor = 10 ** digits
    return math.floor(value * factor) / factor


def _calculate_sub_index(
    concentration: float,
    breakpoints: list[tuple[float, float, int, int]],
    truncate_digits: int,
) -> Optional[int]:
    normalized = _truncate(concentration, truncate_digits)

    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= normalized <= c_high:
            sub_index = ((i_high - i_low) / (c_high - c_low)) * (normalized - c_low) + i_low
            return round(sub_index)

    if normalized > breakpoints[-1][1]:
        return 500

    return None


def _calculate_aqi_from_pollutants(pm25: float, pm10: float) -> int:
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
    return max(valid_indices, default=0)


def _get_dominant_pollutant(pm25: float, pm10: float, no2: float = 0.0, o3: float = 0.0) -> str:
    pollutant_levels = {
        "PM2.5": _safe_float(pm25),
        "PM10": _safe_float(pm10),
        "NO2": _safe_float(no2),
        "O3": _safe_float(o3),
    }
    dominant_name, dominant_value = max(pollutant_levels.items(), key=lambda item: item[1])
    return dominant_name if dominant_value > 0 else "Unknown"


def _build_empty_aqi_payload(lat: float, lng: float, location: Optional[str] = None) -> dict:
    return {
        "aqi": 0,
        "location": location or f"Lat: {lat:.2f}, Lng: {lng:.2f}",
        "lat": lat,
        "lng": lng,
        "pm25": 0.0,
        "pm10": 0.0,
        "no2": 0.0,
        "o3": 0.0,
        "so2": 0.0,
        "category": "No Data",
        "dominant_pollutant": "Unknown",
        "aqi_method": "fallback_zero",
    }


def _build_empty_history(days: int = DEFAULT_HISTORY_DAYS) -> list[dict[str, Any]]:
    safe_days = max(1, min(days, 14))
    today = datetime.now(timezone.utc).date()
    history = []

    for offset in range(safe_days - 1, -1, -1):
        day = today - timedelta(days=offset)
        history.append(
            {
                "date": day.isoformat(),
                "day": day.strftime("%a"),
                "aqi": 0,
                "pm25": 0.0,
                "pm10": 0.0,
                "o3": 0.0,
                "no2": 0.0,
                "so2": 0.0,
                "samples": 0,
            }
        )

    return history


def _summarize_history_entries(entries: list[dict[str, Any]], days: int = DEFAULT_HISTORY_DAYS) -> list[dict[str, Any]]:
    summary = {item["date"]: item.copy() for item in _build_empty_history(days)}

    for entry in entries or []:
        timestamp = entry.get("dt")
        if not timestamp:
            continue

        day_key = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).date().isoformat()
        bucket = summary.get(day_key)
        if not bucket:
            continue

        components = entry.get("components") or {}
        bucket["pm25"] += _safe_float(components.get("pm2_5"))
        bucket["pm10"] += _safe_float(components.get("pm10"))
        bucket["o3"] += _safe_float(components.get("o3"))
        bucket["no2"] += _safe_float(components.get("no2"))
        bucket["so2"] += _safe_float(components.get("so2"))
        bucket["samples"] += 1

    history = []
    for date_key in sorted(summary.keys()):
        bucket = summary[date_key]
        samples = bucket["samples"]

        if samples > 0:
            pm25 = round(bucket["pm25"] / samples, 2)
            pm10 = round(bucket["pm10"] / samples, 2)
            o3 = round(bucket["o3"] / samples, 2)
            no2 = round(bucket["no2"] / samples, 2)
            so2 = round(bucket["so2"] / samples, 2)
            aqi = _calculate_aqi_from_pollutants(pm25, pm10)
        else:
            pm25 = pm10 = o3 = no2 = so2 = 0.0
            aqi = 0

        history.append(
            {
                "date": date_key,
                "day": bucket["day"],
                "aqi": aqi,
                "pm25": pm25,
                "pm10": pm10,
                "o3": o3,
                "no2": no2,
                "so2": so2,
                "samples": samples,
            }
        )

    return history


async def _fetch_location_name(lat: float, lng: float) -> str:
    if not OPENWEATHER_API_KEY:
        return f"Lat: {lat:.2f}, Lng: {lng:.2f}"

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                OPENWEATHER_REVERSE_GEO_URL,
                params={"lat": lat, "lon": lng, "limit": 1, "appid": OPENWEATHER_API_KEY},
            )

        if response.status_code == 200:
            data = response.json() or []
            if data:
                loc = data[0]
                parts = [part for part in [loc.get("name"), loc.get("state"), loc.get("country")] if part]
                if parts:
                    return ", ".join(parts)
    except Exception as exc:
        logger.warning("[AQI Service] Reverse geocoding failed: %s", exc)

    return f"Lat: {lat:.2f}, Lng: {lng:.2f}"


async def search_locations(query: str, limit: int = 5) -> Dict[str, Any]:
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
                params={"q": normalized_query, "limit": capped_limit, "appid": OPENWEATHER_API_KEY},
            )

        if response.status_code != 200:
            logger.error("[AQI Service] City search API error: %s", response.status_code)
            return _envelope(
                data={"query": normalized_query, "suggestions": []},
                status="fallback",
                source="mock",
                error=f"OpenWeather API returned {response.status_code}",
            )

        suggestions = []
        seen_keys = set()

        for item in response.json() or []:
            city = (item.get("name") or "").strip()
            state = (item.get("state") or "").strip()
            country = (item.get("country") or "").strip()
            lat = item.get("lat")
            lng = item.get("lon")

            if not city or lat is None or lng is None:
                continue

            key = (city.lower(), state.lower(), country.lower(), round(float(lat), 4), round(float(lng), 4))
            if key in seen_keys:
                continue

            seen_keys.add(key)
            parts = [part for part in [city, state, country] if part]
            suggestions.append(
                {
                    "name": city,
                    "state": state,
                    "country": country,
                    "label": ", ".join(parts),
                    "lat": round(float(lat), 6),
                    "lng": round(float(lng), 6),
                }
            )

        return _envelope(
            data={"query": normalized_query, "suggestions": suggestions},
            status="ready",
            source="openweather",
        )
    except httpx.RequestError as exc:
        logger.error("[AQI Service] City search network error: %s", exc)
        return _envelope(
            data={"query": normalized_query, "suggestions": []},
            status="fallback",
            source="mock",
            error=str(exc),
        )
    except Exception as exc:
        logger.error("[AQI Service] City search unexpected error: %s", exc)
        return _envelope(
            data={"query": normalized_query, "suggestions": []},
            status="fallback",
            source="mock",
            error="Failed to search cities",
        )


async def get_aqi_data(lat: float, lng: float) -> Dict[str, Any]:
    if not OPENWEATHER_API_KEY:
        logger.error("[AQI Service] OPENWEATHER_API_KEY not configured")
        return _envelope(
            data=_build_empty_aqi_payload(lat, lng, "AQI data unavailable"),
            status="fallback",
            source="mock",
            error="API key not configured",
        )

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(
                OPENWEATHER_AQI_URL,
                params={"lat": lat, "lon": lng, "appid": OPENWEATHER_API_KEY},
            )

        location_name = await _fetch_location_name(lat, lng)

        if response.status_code != 200:
            logger.error("[AQI Service] OpenWeather API error: %s", response.status_code)
            return _envelope(
                data=_build_empty_aqi_payload(lat, lng, location_name),
                status="fallback",
                source="mock",
                error=f"OpenWeather API returned {response.status_code}",
            )

        readings = (response.json() or {}).get("list") or []
        current_reading = readings[0] if readings else {}
        components = current_reading.get("components") or {}

        pm25 = round(_safe_float(components.get("pm2_5")), 2)
        pm10 = round(_safe_float(components.get("pm10")), 2)
        no2 = round(_safe_float(components.get("no2")), 2)
        o3 = round(_safe_float(components.get("o3")), 2)
        so2 = round(_safe_float(components.get("so2")), 2)
        has_measurements = any(value > 0 for value in [pm25, pm10, no2, o3, so2])
        aqi_standard = _calculate_aqi_from_pollutants(pm25, pm10) if has_measurements else 0

        return _envelope(
            data={
                "aqi": int(aqi_standard),
                "location": location_name,
                "lat": lat,
                "lng": lng,
                "pm25": pm25,
                "pm10": pm10,
                "no2": no2,
                "o3": o3,
                "so2": so2,
                "category": _get_aqi_category(int(aqi_standard)) if has_measurements else "No Data",
                "dominant_pollutant": _get_dominant_pollutant(pm25, pm10, no2, o3),
                "aqi_method": "openweather_pm_epa_interp" if has_measurements else "openweather_empty",
            },
            status="ready",
            source="openweather",
        )
    except httpx.RequestError as exc:
        logger.error("[AQI Service] Network error: %s", exc)
        location_name = await _fetch_location_name(lat, lng)
        return _envelope(
            data=_build_empty_aqi_payload(lat, lng, location_name),
            status="fallback",
            source="mock",
            error=str(exc),
        )
    except Exception as exc:
        logger.error("[AQI Service] Unexpected error: %s", exc)
        return _envelope(
            data=_build_empty_aqi_payload(lat, lng, "Error retrieving location"),
            status="fallback",
            source="mock",
            error="Failed to fetch AQI data",
        )


async def get_aqi_history(lat: float, lng: float, days: int = DEFAULT_HISTORY_DAYS) -> Dict[str, Any]:
    safe_days = max(1, min(days, 14))
    history_fallback = _build_empty_history(safe_days)

    if not OPENWEATHER_API_KEY:
        logger.error("[AQI Service] OPENWEATHER_API_KEY not configured for history")
        return _envelope(
            data={"history": history_fallback},
            status="fallback",
            source="mock",
            error="API key not configured",
        )

    end_time = int(datetime.now(timezone.utc).timestamp())
    start_time = int((datetime.now(timezone.utc) - timedelta(days=safe_days - 1, hours=23)).timestamp())

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                OPENWEATHER_HISTORY_URL,
                params={
                    "lat": lat,
                    "lon": lng,
                    "start": start_time,
                    "end": end_time,
                    "appid": OPENWEATHER_API_KEY,
                },
            )

        if response.status_code != 200:
            logger.error("[AQI Service] OpenWeather history API error: %s", response.status_code)
            return _envelope(
                data={"history": history_fallback},
                status="fallback",
                source="mock",
                error=f"OpenWeather API returned {response.status_code}",
            )

        entries = (response.json() or {}).get("list") or []
        return _envelope(
            data={"history": _summarize_history_entries(entries, safe_days)},
            status="ready",
            source="openweather",
        )
    except httpx.RequestError as exc:
        logger.error("[AQI Service] History network error: %s", exc)
        return _envelope(
            data={"history": history_fallback},
            status="fallback",
            source="mock",
            error=str(exc),
        )
    except Exception as exc:
        logger.error("[AQI Service] History unexpected error: %s", exc)
        return _envelope(
            data={"history": history_fallback},
            status="fallback",
            source="mock",
            error="Failed to fetch AQI history",
        )
