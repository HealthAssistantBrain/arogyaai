from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services import aqi_service


def test_build_empty_history_returns_requested_number_of_days():
    history = aqi_service._build_empty_history(7)

    assert len(history) == 7
    assert all(item["aqi"] == 0 for item in history)
    assert all(item["pm25"] == 0 for item in history)


def test_summarize_history_entries_aggregates_daily_pollutants():
    now = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    yesterday = now - timedelta(days=1)
    entries = [
        {
            "dt": int(now.timestamp()),
            "components": {
                "pm2_5": 30.0,
                "pm10": 60.0,
                "o3": 40.0,
                "no2": 22.0,
                "so2": 8.0,
            },
        },
        {
            "dt": int((now + timedelta(hours=2)).timestamp()),
            "components": {
                "pm2_5": 50.0,
                "pm10": 90.0,
                "o3": 60.0,
                "no2": 28.0,
                "so2": 10.0,
            },
        },
        {
            "dt": int(yesterday.timestamp()),
            "components": {
                "pm2_5": 12.0,
                "pm10": 30.0,
                "o3": 18.0,
                "no2": 10.0,
                "so2": 4.0,
            },
        },
    ]

    history = aqi_service._summarize_history_entries(entries, 2)

    assert len(history) == 2
    assert history[0]["date"] == yesterday.date().isoformat()
    assert history[0]["pm25"] == 12.0
    assert history[0]["samples"] == 1
    assert history[1]["date"] == now.date().isoformat()
    assert history[1]["pm25"] == 40.0
    assert history[1]["pm10"] == 75.0
    assert history[1]["o3"] == 50.0
    assert history[1]["no2"] == 25.0
    assert history[1]["so2"] == 9.0
    assert history[1]["aqi"] > 0


def test_build_empty_aqi_payload_uses_zero_fallback_contract():
    payload = aqi_service._build_empty_aqi_payload(12.34, 56.78, "Fallback")

    assert payload == {
        "aqi": 0,
        "location": "Fallback",
        "lat": 12.34,
        "lng": 56.78,
        "pm25": 0.0,
        "pm10": 0.0,
        "no2": 0.0,
        "o3": 0.0,
        "so2": 0.0,
        "category": "No Data",
        "dominant_pollutant": "Unknown",
        "aqi_method": "fallback_zero",
    }
