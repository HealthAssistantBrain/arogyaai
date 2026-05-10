"""
dashboard_service.py
====================
Unified service layer for all dashboard data.

Each method returns a pipeline-compatible envelope:

    {
        "success":      bool,
        "status":       "ready" | "processing" | "fallback",
        "source":       "ml" | "wearable" | "computed" | "mock",
        "data":         {...},
        "last_updated": ISO-8601 string,
        "alerts":       [...],   # only on get_alerts()
    }

Adding a real ML/wearable data-source in the future requires ONLY changing
the corresponding private _fetch_*() helper — the route layer and frontend
contract stay identical.
"""

from __future__ import annotations

import logging
import math
from hashlib import sha256
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from core.config import settings
from models import GoogleFitConnection, User, UserVital, UserVitalTypeEnum, WearableMetric
from services.recommendation_engine import generate_recommendation_plan
from services.recommendation_service import generate_test_recommendations

logger = logging.getLogger(__name__)
ROLLING_WINDOW_HOURS = 24
COMPARISON_WINDOW_HOURS = 48
STEP_STREAK_WINDOW_DAYS = 7
RECENT_EMPTY_MESSAGES = {
    "steps": "No recent step data",
    "heart_rate": "No recent heart rate data",
    "sleep": "No recent sleep data",
    "spo2": "No recent SpO2 data",
    "glucose": "No recent glucose data",
    "body_temperature": "No recent temperature data",
    "blood_pressure": "No recent blood pressure data",
    "resting_hr": "No recent resting heart rate data",
    "recovery": "No recent recovery data",
}
TREND_EPSILON = {
    "steps": 50.0,
    "heart_rate": 1.0,
    "sleep": 0.1,
    "spo2": 0.2,
    "glucose": 1.0,
    "body_temperature": 0.1,
    "resting_hr": 1.0,
    "recovery": 1.0,
}
GLUCOSE_MGDL_PER_MMOLL = 18.0
SUPPORTED_METRIC_RANGES = {"24h", "7d"}
METRIC_RANGE_LOOKBACK = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}
METRIC_RANGE_BUCKETS = {
    "24h": 24,
    "7d": 7,
}
CONTINUITY_LOOKBACK_DAYS = 14
DEFAULT_TIMEZONE = "Asia/Kolkata"
DEFAULT_METRIC_BASELINES = {
    "heart_rate": 72.0,
    "spo2": 97.5,
    "glucose": 98.0,
    "body_temperature": 36.7,
    "temperature": 36.7,
    "steps": 6800.0,
    "sleep": 7.2,
    "resting_hr": 61.0,
    "recovery": 76.0,
    "blood_pressure_systolic": 118.0,
    "blood_pressure_diastolic": 76.0,
}
METRIC_VALUE_BOUNDS = {
    "heart_rate": (42.0, 165.0),
    "spo2": (92.0, 100.0),
    "glucose": (68.0, 210.0),
    "body_temperature": (35.9, 38.1),
    "temperature": (35.9, 38.1),
    "steps": (0.0, 18000.0),
    "sleep": (0.0, 10.5),
    "resting_hr": (44.0, 92.0),
    "recovery": (30.0, 98.0),
    "blood_pressure_systolic": (96.0, 158.0),
    "blood_pressure_diastolic": (58.0, 102.0),
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_timezone_name(db: Session, user: User, timezone_name: str | None = None) -> str:
    candidates = [timezone_name]
    try:
        connection = (
            db.query(GoogleFitConnection)
            .filter(GoogleFitConnection.user_id == user.id)
            .first()
        )
    except Exception:
        connection = None
    if connection is not None:
        candidates.append(getattr(connection, "default_timezone", None))
    candidates.append(settings.GOOGLE_FIT_DEFAULT_TIMEZONE)
    candidates.append(DEFAULT_TIMEZONE)

    for candidate in candidates:
        if not candidate:
            continue
        try:
            ZoneInfo(str(candidate))
            return str(candidate)
        except Exception:
            continue
    return DEFAULT_TIMEZONE


def _timezone_info(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except Exception:
        return ZoneInfo(DEFAULT_TIMEZONE)


def _normalize_metric_range(range_value: str | None) -> str:
    candidate = str(range_value or "24h").strip().lower()
    if candidate not in SUPPORTED_METRIC_RANGES:
        candidate = "24h"
    return candidate


def _bucket_grid(range_value: str, timezone_name: str) -> tuple[list[datetime], datetime, datetime]:
    tzinfo = _timezone_info(timezone_name)
    now_local = datetime.now(tzinfo)
    normalized_range = _normalize_metric_range(range_value)
    if normalized_range == "7d":
        current_day = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        bucket_starts = [current_day - timedelta(days=6 - index) for index in range(7)]
        window_start = bucket_starts[0].astimezone(timezone.utc)
        window_end = (bucket_starts[-1] + timedelta(days=1)).astimezone(timezone.utc)
        return bucket_starts, window_start, window_end

    end_local = now_local.replace(minute=0, second=0, microsecond=0)
    bucket_starts = [end_local - timedelta(hours=23 - index) for index in range(24)]
    window_start = bucket_starts[0].astimezone(timezone.utc)
    window_end = (bucket_starts[-1] + timedelta(hours=1)).astimezone(timezone.utc)
    return bucket_starts, window_start, window_end


def _bucket_key(dt: datetime, range_value: str, timezone_name: str) -> datetime:
    tzinfo = _timezone_info(timezone_name)
    localized = dt.astimezone(tzinfo)
    if range_value == "7d":
        return localized.replace(hour=0, minute=0, second=0, microsecond=0)
    return localized.replace(minute=0, second=0, microsecond=0)


def _expand_query_window(window_start: datetime) -> datetime:
    return window_start - timedelta(days=CONTINUITY_LOOKBACK_DAYS)


def _series_last_timestamp(points: list[dict[str, Any]]) -> str | None:
    timestamps = [point.get("timestamp") for point in points if point.get("timestamp")]
    return timestamps[-1] if timestamps else None


def _clamp_metric_value(metric_name: str, value: float | None) -> float | None:
    if value is None:
        return None
    lower, upper = METRIC_VALUE_BOUNDS.get(metric_name, (None, None))
    numeric = float(value)
    if lower is not None:
        numeric = max(lower, numeric)
    if upper is not None:
        numeric = min(upper, numeric)
    return round(numeric, 1)


def _stable_phase(metric_name: str, user_id: Any, *, modulus: float = math.tau) -> float:
    digest = sha256(f"{user_id}:{metric_name}".encode("utf-8")).hexdigest()
    seed = int(digest[:12], 16) / float(16**12)
    return seed * modulus


def _gaussian(hour_value: float, center: float, spread: float) -> float:
    if spread <= 0:
        return 0.0
    return math.exp(-((hour_value - center) ** 2) / (2 * spread * spread))


def _daily_steps_weights(day_anchor: datetime, user_id: Any) -> list[float]:
    phase = _stable_phase("steps", user_id, modulus=1.6)
    weights: list[float] = []
    for hour in range(24):
        commuter = 1.45 * _gaussian(hour, 8.2 + phase, 1.8)
        midday = 0.95 * _gaussian(hour, 13.2, 2.4)
        evening = 1.85 * _gaussian(hour, 18.7 - phase * 0.5, 2.6)
        baseline = 0.02 if hour < 5 else 0.08
        weekday_boost = 1.08 if day_anchor.weekday() < 5 else 0.92
        weights.append(max(0.01, (baseline + commuter + midday + evening) * weekday_boost))
    return weights


def _default_metric_signal(metric_name: str, at_local: datetime, user_id: Any, baseline: float) -> float:
    hour_value = at_local.hour + (at_local.minute / 60.0)
    phase = _stable_phase(metric_name, user_id, modulus=2.4)

    if metric_name == "heart_rate":
        return baseline - 11.5 * _gaussian(hour_value, 3.3 + phase * 0.1, 2.1) + 8.8 * _gaussian(hour_value, 8.4, 1.7) + 7.5 * _gaussian(hour_value, 18.1, 2.7)
    if metric_name == "resting_hr":
        return baseline - 8.0 * _gaussian(hour_value, 3.0 + phase * 0.1, 2.3) + 2.0 * _gaussian(hour_value, 17.0, 3.0)
    if metric_name == "spo2":
        return baseline + 0.45 * math.sin(((hour_value - 15.0) / 24.0) * math.tau + phase * 0.2) - 0.5 * _gaussian(hour_value, 4.0, 2.4)
    if metric_name == "glucose":
        return baseline + 17.0 * _gaussian(hour_value, 8.2 + phase * 0.1, 1.1) + 20.0 * _gaussian(hour_value, 13.0, 1.2) + 16.0 * _gaussian(hour_value, 19.8 - phase * 0.1, 1.4) - 4.5 * _gaussian(hour_value, 3.4, 2.2)
    if metric_name in {"body_temperature", "temperature"}:
        return baseline - 0.25 * _gaussian(hour_value, 4.0, 2.8) + 0.32 * _gaussian(hour_value, 17.2, 3.3)
    if metric_name == "blood_pressure_systolic":
        return baseline + 7.5 * _gaussian(hour_value, 8.8, 2.0) + 5.0 * _gaussian(hour_value, 18.0, 2.8) - 4.2 * _gaussian(hour_value, 3.2, 2.3)
    if metric_name == "blood_pressure_diastolic":
        return baseline + 4.0 * _gaussian(hour_value, 9.0, 2.1) + 3.2 * _gaussian(hour_value, 18.2, 2.9) - 2.2 * _gaussian(hour_value, 3.3, 2.3)
    if metric_name == "sleep":
        return baseline
    if metric_name == "recovery":
        wake_rebound = 8.0 * _gaussian(hour_value, 8.4, 2.3)
        daytime_drain = 10.0 * _gaussian(hour_value, 17.5, 4.5)
        overnight = 6.0 * _gaussian(hour_value, 3.0, 2.1)
        return baseline + wake_rebound + overnight - daytime_drain

    return baseline


def _series_observed_average(points: list[dict[str, Any]], metric_name: str) -> float | None:
    values = [
        float(point["value"])
        for point in points
        if point.get("source") == "observed" and point.get("value") is not None
    ]
    if not values and metric_name == "sleep":
        values = [float(point["value"]) for point in points if point.get("value") is not None]
    return round(sum(values) / len(values), 2) if values else None


def _coerce_row_value(row: UserVital, vital_type: UserVitalTypeEnum) -> float | None:
    if vital_type == UserVitalTypeEnum.GLUCOSE:
        normalized_unit = _canonical_glucose_unit(getattr(row, "raw_unit", None) or getattr(row, "normalized_unit", None) or row.unit) or "mg/dL"
        normalized_value = (
            float(row.raw_value)
            if getattr(row, "raw_value", None) is not None
            else (
                float(row.normalized_value)
                if getattr(row, "normalized_value", None) is not None
                else (float(row.value) if row.value is not None else None)
            )
        )
        return _convert_glucose_value(normalized_value, normalized_unit, normalized_unit)

    value_raw = (
        float(row.normalized_value)
        if getattr(row, "normalized_value", None) is not None
        else (float(row.value) if row.value is not None else None)
    )
    normalized_value, _normalized_unit = _normalize_metric_value(vital_type, value_raw, getattr(row, "normalized_unit", None) or row.unit)
    return normalized_value


def _query_metric_rows(
    db: Session,
    user: User,
    vital_type: UserVitalTypeEnum,
    start_at: datetime,
    end_at: datetime,
) -> list[UserVital]:
    return (
        db.query(UserVital)
        .filter(
            UserVital.user_id == user.id,
            UserVital.vital_type == vital_type,
            UserVital.timestamp >= start_at,
            UserVital.timestamp < end_at,
        )
        .order_by(UserVital.timestamp.asc())
        .all()
    )


def _actual_bucket_values(
    rows: list[UserVital],
    metric_name: str,
    vital_type: UserVitalTypeEnum,
    range_value: str,
    timezone_name: str,
) -> dict[datetime, list[float]]:
    bucketed: dict[datetime, list[float]] = {}
    for row in rows:
        if row.timestamp is None:
            continue
        value = _coerce_row_value(row, vital_type)
        if value is None:
            continue
        key = _bucket_key(row.timestamp, range_value, timezone_name)
        bucketed.setdefault(key, []).append(float(value))
    return bucketed


def _build_continuous_series(
    *,
    metric_name: str,
    range_value: str,
    timezone_name: str,
    user_id: Any,
    observed_buckets: dict[datetime, list[float]],
    bucket_starts: list[datetime],
    unit: str,
) -> list[dict[str, Any]]:
    baseline = _average([_average(values) for values in observed_buckets.values() if values]) or DEFAULT_METRIC_BASELINES.get(metric_name, 0.0)
    series: list[dict[str, Any]] = []
    actual_values = {
        bucket: round(sum(values) / len(values), 1)
        for bucket, values in observed_buckets.items()
        if values
    }

    for index, bucket_start in enumerate(bucket_starts):
        observed_value = actual_values.get(bucket_start)
        if observed_value is not None:
            source = "observed"
            value = observed_value
        else:
            profile_value = _default_metric_signal(metric_name, bucket_start, user_id, baseline)
            previous_index = next((candidate for candidate in range(index - 1, -1, -1) if bucket_starts[candidate] in actual_values), None)
            next_index = next((candidate for candidate in range(index + 1, len(bucket_starts)) if bucket_starts[candidate] in actual_values), None)
            previous_observed = actual_values.get(bucket_starts[previous_index]) if previous_index is not None else None
            next_observed = actual_values.get(bucket_starts[next_index]) if next_index is not None else None
            if previous_observed is not None and next_observed is not None:
                gap = max(1, next_index - previous_index)
                progress = 0.5 if gap <= 1 else (index - previous_index) / gap
                interpolated = previous_observed + ((next_observed - previous_observed) * progress)
                value = (interpolated * 0.62) + (profile_value * 0.38)
                source = "blended"
            elif previous_observed is not None:
                value = (previous_observed * 0.6) + (profile_value * 0.4)
                source = "estimated"
            elif next_observed is not None:
                value = (next_observed * 0.56) + (profile_value * 0.44)
                source = "estimated"
            else:
                value = profile_value
                source = "estimated"
        clamped = _clamp_metric_value(metric_name, value)
        series.append(
            {
                "timestamp": bucket_start.astimezone(timezone.utc).isoformat(),
                "value": clamped,
                "unit": unit,
                "source": source,
            }
        )

    return series


def _build_steps_series(
    *,
    range_value: str,
    timezone_name: str,
    user_id: Any,
    rows: list[UserVital],
    bucket_starts: list[datetime],
) -> tuple[list[dict[str, Any]], float | None]:
    day_totals: dict[str, float] = {}
    for row in rows:
        if row.timestamp is None:
            continue
        local_day = row.timestamp.astimezone(_timezone_info(timezone_name)).date().isoformat()
        day_totals[local_day] = max(day_totals.get(local_day, 0.0), float(row.value or 0.0))

    if range_value == "7d":
        ordered_days = sorted({bucket.date().isoformat() for bucket in bucket_starts})
        observed = [day_totals[day] for day in ordered_days if day in day_totals]
        baseline = _average(observed) or DEFAULT_METRIC_BASELINES["steps"]
        series = []
        for bucket_start in bucket_starts:
            day_key = bucket_start.date().isoformat()
            observed_value = day_totals.get(day_key)
            value = observed_value if observed_value is not None else (baseline * (1.05 if bucket_start.weekday() < 5 else 0.93))
            series.append(
                {
                    "timestamp": bucket_start.astimezone(timezone.utc).isoformat(),
                    "value": round(max(0.0, value)),
                    "unit": "count",
                    "source": "observed" if observed_value is not None else "estimated",
                }
            )
        latest_value = series[-1]["value"] if series else None
        return series, latest_value

    by_day: dict[str, list[datetime]] = {}
    for bucket_start in bucket_starts:
        by_day.setdefault(bucket_start.date().isoformat(), []).append(bucket_start)

    observed = list(day_totals.values())
    baseline = _average(observed) or DEFAULT_METRIC_BASELINES["steps"]
    series: list[dict[str, Any]] = []
    today_key = bucket_starts[-1].date().isoformat() if bucket_starts else None
    current_day_total = 0.0
    for day_key, day_buckets in by_day.items():
        weights = _daily_steps_weights(day_buckets[0], user_id)
        total_weight = sum(weights) or 1.0
        target_total = day_totals.get(day_key, baseline * (1.05 if day_buckets[0].weekday() < 5 else 0.92))
        observed_day = day_key in day_totals
        for bucket_start in day_buckets:
            value = (target_total * weights[bucket_start.hour]) / total_weight
            rounded = round(max(0.0, value))
            series.append(
                {
                    "timestamp": bucket_start.astimezone(timezone.utc).isoformat(),
                    "value": rounded,
                    "unit": "count",
                    "source": "observed" if observed_day else "estimated",
                }
            )
            if day_key == today_key:
                current_day_total += rounded
    return series, round(current_day_total)


def _sleep_session_window(day_anchor: datetime, user_id: Any) -> tuple[float, float]:
    phase = _stable_phase("sleep", user_id, modulus=1.4)
    start_hour = 22.4 + math.sin(phase) * 0.85
    duration = 7.0 + math.cos(phase * 1.2) * 0.55
    return start_hour, duration


def _build_sleep_series(
    *,
    range_value: str,
    timezone_name: str,
    user_id: Any,
    rows: list[UserVital],
    bucket_starts: list[datetime],
) -> tuple[list[dict[str, Any]], float | None]:
    day_totals: dict[str, float] = {}
    for row in rows:
        if row.timestamp is None:
            continue
        normalized_value, _normalized_unit = _normalize_metric_value(UserVitalTypeEnum.SLEEP, float(row.value), row.unit)
        if normalized_value is None:
            continue
        day_totals[row.timestamp.astimezone(_timezone_info(timezone_name)).date().isoformat()] = float(normalized_value)

    observed = list(day_totals.values())
    baseline = _average(observed) or DEFAULT_METRIC_BASELINES["sleep"]

    if range_value == "7d":
        series = []
        for bucket_start in bucket_starts:
            day_key = bucket_start.date().isoformat()
            observed_value = day_totals.get(day_key)
            value = observed_value if observed_value is not None else baseline + (0.25 if bucket_start.weekday() >= 5 else -0.1)
            series.append(
                {
                    "timestamp": bucket_start.astimezone(timezone.utc).isoformat(),
                    "value": round(max(0.0, value), 2),
                    "unit": "hours",
                    "source": "observed" if observed_value is not None else "estimated",
                }
            )
        latest_value = series[-1]["value"] if series else None
        return series, latest_value

    by_day: dict[str, list[datetime]] = {}
    for bucket_start in bucket_starts:
        by_day.setdefault(bucket_start.date().isoformat(), []).append(bucket_start)

    series: list[dict[str, Any]] = []
    latest_value = baseline
    for day_key, day_buckets in by_day.items():
        start_hour, duration = _sleep_session_window(day_buckets[0], user_id)
        total_hours = day_totals.get(day_key, baseline)
        latest_value = total_hours
        observed_day = day_key in day_totals
        for bucket_start in day_buckets:
            overlap = 0.0
            for offset_day in (-1, 0):
                session_day = bucket_start.date() + timedelta(days=offset_day)
                session_start_local = datetime(session_day.year, session_day.month, session_day.day, tzinfo=bucket_start.tzinfo) + timedelta(hours=start_hour)
                session_end_local = session_start_local + timedelta(hours=duration)
                bucket_end = bucket_start + timedelta(hours=1)
                overlap_start = max(bucket_start, session_start_local)
                overlap_end = min(bucket_end, session_end_local)
                if overlap_end > overlap_start:
                    overlap += (overlap_end - overlap_start).total_seconds() / 3600.0
            normalized_overlap = max(0.0, min(1.0, overlap))
            value = round((total_hours / max(duration, 0.1)) * normalized_overlap, 2)
            series.append(
                {
                    "timestamp": bucket_start.astimezone(timezone.utc).isoformat(),
                    "value": value,
                    "unit": "hours",
                    "source": "observed" if observed_day else "estimated",
                }
            )
    return series, round(latest_value, 2)


def _resting_hr_from_series(series: list[dict[str, Any]]) -> float | None:
    values = [float(point["value"]) for point in series if point.get("value") is not None]
    return round(_percentile(values, 18.0), 1) if values else None


def _build_recovery_series(
    *,
    range_value: str,
    timezone_name: str,
    user_id: Any,
    bucket_starts: list[datetime],
    sleep_series: list[dict[str, Any]],
    steps_series: list[dict[str, Any]],
    heart_rate_series: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], float | None]:
    sleep_lookup = {point["timestamp"]: float(point["value"]) for point in sleep_series if point.get("timestamp")}
    steps_lookup = {point["timestamp"]: float(point["value"]) for point in steps_series if point.get("timestamp")}
    hr_values = [float(point["value"]) for point in heart_rate_series if point.get("value") is not None]
    baseline_hr = _average(hr_values) or DEFAULT_METRIC_BASELINES["heart_rate"]
    resting_hr = _resting_hr_from_series(heart_rate_series) or DEFAULT_METRIC_BASELINES["resting_hr"]

    if range_value == "7d":
        daily_sleep = [float(point["value"]) for point in sleep_series if point.get("value") is not None]
        daily_steps = [float(point["value"]) for point in steps_series if point.get("value") is not None]
        avg_sleep = _average(daily_sleep) or DEFAULT_METRIC_BASELINES["sleep"]
        avg_steps = _average(daily_steps) or DEFAULT_METRIC_BASELINES["steps"]
        series = []
        for bucket_start in bucket_starts:
            timestamp = bucket_start.astimezone(timezone.utc).isoformat()
            sleep_hours = next((float(point["value"]) for point in sleep_series if point.get("timestamp") == timestamp), avg_sleep)
            steps_total = next((float(point["value"]) for point in steps_series if point.get("timestamp") == timestamp), avg_steps)
            score = 52.0 + min(26.0, sleep_hours * 3.4) + max(-10.0, 8.0 - (steps_total / 2200.0)) + max(-10.0, 74.0 - resting_hr)
            series.append(
                {
                    "timestamp": timestamp,
                    "value": _clamp_metric_value("recovery", score),
                    "unit": "%",
                    "source": "blended",
                }
            )
        return series, series[-1]["value"] if series else None

    series = []
    current_value = None
    for bucket_start in bucket_starts:
        timestamp = bucket_start.astimezone(timezone.utc).isoformat()
        sleep_component = min(8.0, sleep_lookup.get(timestamp, 0.0)) * 5.4
        step_drain = min(12.0, steps_lookup.get(timestamp, 0.0) / 160.0)
        hr_value = next((float(point["value"]) for point in heart_rate_series if point.get("timestamp") == timestamp and point.get("value") is not None), baseline_hr)
        stability = max(-8.0, min(8.0, (baseline_hr - hr_value) * 0.9))
        profile = _default_metric_signal("recovery", bucket_start, user_id, DEFAULT_METRIC_BASELINES["recovery"])
        score = profile + sleep_component - step_drain + stability + max(-6.0, 70.0 - resting_hr)
        current_value = _clamp_metric_value("recovery", score)
        series.append(
            {
                "timestamp": timestamp,
                "value": current_value,
                "unit": "%",
                "source": "blended",
            }
        )
    return series, current_value


def _metric_payload_from_series(
    *,
    metric_name: str,
    unit: str,
    range_value: str,
    timezone_name: str,
    series: list[dict[str, Any]],
    current_value: float | None = None,
    precision: int | None = None,
    source_override: str | None = None,
) -> dict[str, Any]:
    values = [float(point["value"]) for point in series if point.get("value") is not None]
    current = current_value if current_value is not None else (values[-1] if values else None)
    previous = values[-2] if len(values) > 1 else None
    delta = None if current is None or previous is None else round(float(current) - float(previous), 2)
    source = source_override or (
        "observed"
        if all(point.get("source") == "observed" for point in series if point.get("value") is not None)
        else ("blended" if any(point.get("source") == "observed" for point in series) else "simulated_continuity")
    )
    return {
        "value": round(float(current), precision) if current is not None and precision is not None else current,
        "current": round(float(current), precision) if current is not None and precision is not None else current,
        "previous": round(float(previous), precision) if previous is not None and precision is not None else previous,
        "delta": delta,
        "trend": _trend_from_delta(metric_name, delta),
        "unit": unit,
        "precision": precision,
        "status": "ready" if current is not None else "no_data",
        "source": source,
        "last_updated": _series_last_timestamp(series),
        "series": series,
        "window": range_value,
        "window_start": series[0]["timestamp"] if series else None,
        "window_end": series[-1]["timestamp"] if series else None,
        "timezone": timezone_name,
        "bucket_count": len(series),
        "empty_message": None if current is not None else RECENT_EMPTY_MESSAGES.get(metric_name, "No recent data"),
    }


def _envelope(data: dict, status: str, source: str, error: Optional[str] = None) -> dict:
    return {
        "success": error is None,
        "status": status,          # "ready" | "processing" | "fallback"
        "source": source,          # "ml" | "wearable" | "computed" | "mock"
        "data": data,
        "error": error,
        "last_updated": _now(),
    }


def _rolling_window_bounds(hours: int = ROLLING_WINDOW_HOURS) -> tuple[datetime, datetime, datetime]:
    current_end = datetime.now(timezone.utc)
    current_start = current_end - timedelta(hours=hours)
    previous_start = current_start - timedelta(hours=hours)
    return previous_start, current_start, current_end


def _normalize_metric_value(vital_type: UserVitalTypeEnum, value: float | None, unit: str | None) -> tuple[float | None, str | None]:
    if value is None:
        return None, unit

    normalized_unit = str(unit or "").strip() or None
    if vital_type == UserVitalTypeEnum.SLEEP and normalized_unit and normalized_unit.lower() in {"minutes", "minute", "min", "mins"}:
        return round(float(value) / 60.0, 2), "hours"
    return float(value), normalized_unit


def _canonical_glucose_unit(unit: str | None) -> str | None:
    normalized = str(unit or "").strip().lower()
    if not normalized:
        return None
    if normalized in {"mmol/l", "mmol"}:
        return "mmol/L"
    if normalized in {"mg/dl", "mgdl"}:
        return "mg/dL"
    return str(unit).strip()


def _convert_glucose_value(value: float | None, from_unit: str | None, to_unit: str | None) -> float | None:
    if value is None:
        return None

    source_unit = _canonical_glucose_unit(from_unit)
    target_unit = _canonical_glucose_unit(to_unit)
    numeric_value = float(value)

    if not source_unit or not target_unit or source_unit == target_unit:
        return round(numeric_value, 1)
    if source_unit == "mmol/L" and target_unit == "mg/dL":
        return round(numeric_value * GLUCOSE_MGDL_PER_MMOLL, 1)
    if source_unit == "mg/dL" and target_unit == "mmol/L":
        return round(numeric_value / GLUCOSE_MGDL_PER_MMOLL, 1)
    return round(numeric_value, 1)


def _trend_from_delta(metric_name: str, delta: float | None) -> str:
    if delta is None:
        return "flat"
    if abs(delta) < TREND_EPSILON.get(metric_name, 0.5):
        return "flat"
    return "up" if delta > 0 else "down"


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if percentile <= 0:
        return ordered[0]
    if percentile >= 100:
        return ordered[-1]
    rank = (len(ordered) - 1) * (percentile / 100.0)
    lower = int(math.floor(rank))
    upper = min(len(ordered) - 1, lower + 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _serialize_vital_series(rows: list[UserVital], vital_type: UserVitalTypeEnum) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for row in rows:
        normalized_value, normalized_unit = _normalize_metric_value(
            vital_type,
            float(row.value) if row.value is not None else None,
            row.unit,
        )
        if normalized_value is None or row.timestamp is None:
            continue
        series.append(
            {
                "value": normalized_value,
                "timestamp": row.timestamp.isoformat(),
                "unit": normalized_unit,
                "type": vital_type.value,
                "source": row.source.value if row.source else "google_fit",
            }
        )
    return series


def _query_vital_rows(
    db: Session,
    user: User,
    vital_type: UserVitalTypeEnum,
    start_at: datetime,
    end_at: datetime,
) -> list[UserVital]:
    return (
        db.query(UserVital)
        .filter(
            UserVital.user_id == user.id,
            UserVital.vital_type == vital_type,
            UserVital.timestamp >= start_at,
            UserVital.timestamp < end_at,
        )
        .order_by(UserVital.timestamp.asc())
        .all()
    )


def _build_metric_payload(
    db: Session,
    user: User,
    metric_name: str,
    vital_type: UserVitalTypeEnum,
    default_unit: str,
) -> dict[str, Any]:
    previous_start, current_start, current_end = _rolling_window_bounds()
    rows = _query_vital_rows(db, user, vital_type, previous_start, current_end)
    current_rows = [row for row in rows if row.timestamp and row.timestamp >= current_start]
    previous_rows = [row for row in rows if row.timestamp and row.timestamp < current_start]

    current_series = _serialize_vital_series(current_rows, vital_type)
    previous_series = _serialize_vital_series(previous_rows, vital_type)
    latest_current = current_series[-1] if current_series else None
    latest_previous = previous_series[-1] if previous_series else None
    current_value = latest_current.get("value") if latest_current else None
    previous_value = latest_previous.get("value") if latest_previous else None
    delta = None if current_value is None or previous_value is None else round(float(current_value) - float(previous_value), 2)
    status = "ready" if latest_current is not None else "no_data"
    last_updated = latest_current.get("timestamp") if latest_current else None
    payload = {
        "value": current_value,
        "current": current_value,
        "previous": previous_value,
        "delta": delta,
        "trend": _trend_from_delta(metric_name, delta),
        "unit": latest_current.get("unit") if latest_current and latest_current.get("unit") else default_unit,
        "status": status,
        "source": latest_current.get("source") if latest_current else "db",
        "last_updated": last_updated,
        "series": current_series,
        "window": "rolling_24h",
        "window_start": current_start.isoformat(),
        "window_end": current_end.isoformat(),
        "empty_message": None if latest_current else RECENT_EMPTY_MESSAGES.get(metric_name, "No recent data"),
    }
    logger.info(
        "METRIC_DB_FETCH | metric_type=%s | user_id=%s | window_start=%s | window_end=%s | series_length=%s | current=%s | previous=%s | source=%s",
        metric_name,
        str(user.id),
        current_start.isoformat(),
        current_end.isoformat(),
        len(current_series),
        current_value,
        previous_value,
        payload["source"],
    )
    return payload


def _glucose_row_payload(row: UserVital) -> dict[str, Any] | None:
    normalized_value = (
        float(row.normalized_value)
        if row.normalized_value is not None
        else (float(row.value) if row.value is not None else None)
    )
    normalized_unit = _canonical_glucose_unit(row.normalized_unit or row.unit) or "mg/dL"

    raw_value = float(row.raw_value) if row.raw_value is not None else None
    raw_unit = _canonical_glucose_unit(row.raw_unit)
    if raw_value is None:
        source_unit = _canonical_glucose_unit(row.unit)
        if source_unit and source_unit != normalized_unit and row.value is not None:
            raw_value = float(row.value)
            raw_unit = source_unit
        else:
            raw_value = normalized_value
            raw_unit = normalized_unit

    if normalized_value is None or row.timestamp is None:
        return None

    return {
        "timestamp": row.timestamp.isoformat(),
        "raw_value": round(float(raw_value), 1) if raw_value is not None else None,
        "raw_unit": raw_unit or normalized_unit,
        "normalized_value": round(float(normalized_value), 1),
        "normalized_unit": normalized_unit,
        "source": row.source.value if row.source else "google_fit",
    }


def _glucose_display_point(point: dict[str, Any], display_unit: str) -> dict[str, Any]:
    display_value = _convert_glucose_value(
        point.get("raw_value"),
        point.get("raw_unit"),
        display_unit,
    )
    if display_value is None:
        display_value = _convert_glucose_value(
            point.get("normalized_value"),
            point.get("normalized_unit"),
            display_unit,
        )

    return {
        "timestamp": point.get("timestamp"),
        "value": display_value,
        "unit": display_unit,
        "raw_value": point.get("raw_value"),
        "raw_unit": point.get("raw_unit"),
        "normalized_value": point.get("normalized_value"),
        "normalized_unit": point.get("normalized_unit"),
        "source": point.get("source"),
    }


def _build_glucose_metric_payload(db: Session, user: User) -> dict[str, Any]:
    previous_start, current_start, current_end = _rolling_window_bounds()
    rows = _query_vital_rows(db, user, UserVitalTypeEnum.GLUCOSE, previous_start, current_end)
    current_rows = [row for row in rows if row.timestamp and row.timestamp >= current_start]
    previous_rows = [row for row in rows if row.timestamp and row.timestamp < current_start]

    current_points = [point for point in (_glucose_row_payload(row) for row in current_rows) if point is not None]
    previous_points = [point for point in (_glucose_row_payload(row) for row in previous_rows) if point is not None]

    latest_current = current_points[-1] if current_points else None
    latest_previous = previous_points[-1] if previous_points else None
    display_unit = _canonical_glucose_unit(latest_current.get("raw_unit") if latest_current else None) or "mg/dL"
    current_series = [_glucose_display_point(point, display_unit) for point in current_points]
    previous_series = [_glucose_display_point(point, display_unit) for point in previous_points]
    current_value = current_series[-1].get("value") if current_series else None
    previous_value = previous_series[-1].get("value") if previous_series else None
    delta = None if current_value is None or previous_value is None else round(float(current_value) - float(previous_value), 2)
    status = "ready" if latest_current is not None else "no_data"
    last_updated = latest_current.get("timestamp") if latest_current else None

    payload = {
        "value": current_value,
        "current": current_value,
        "previous": previous_value,
        "delta": delta,
        "trend": _trend_from_delta("glucose", delta),
        "unit": display_unit,
        "precision": 1 if display_unit == "mmol/L" else 0,
        "status": status,
        "source": latest_current.get("source") if latest_current else "db",
        "last_updated": last_updated,
        "series": current_series,
        "window": "rolling_24h",
        "window_start": current_start.isoformat(),
        "window_end": current_end.isoformat(),
        "empty_message": None if latest_current else RECENT_EMPTY_MESSAGES["glucose"],
        "raw_value": latest_current.get("raw_value") if latest_current else None,
        "raw_unit": latest_current.get("raw_unit") if latest_current else None,
        "normalized_value": latest_current.get("normalized_value") if latest_current else None,
        "normalized_unit": latest_current.get("normalized_unit") if latest_current else "mg/dL",
        "display_value": current_value,
        "display_unit": display_unit,
        "preferred_unit": display_unit,
    }
    logger.info(
        "GLUCOSE_PIPELINE_TRACE | stage=api_response | user_id=%s | raw_value=%s | raw_unit=%s | normalized_value=%s | normalized_unit=%s | display_value=%s | display_unit=%s | series_length=%s",
        str(user.id),
        payload["raw_value"],
        payload["raw_unit"],
        payload["normalized_value"],
        payload["normalized_unit"],
        payload["display_value"],
        payload["display_unit"],
        len(current_series),
    )
    return payload


def _step_streak(db: Session, user: User) -> list[bool]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=STEP_STREAK_WINDOW_DAYS + 2)
    rows = (
        db.query(UserVital)
        .filter(
            UserVital.user_id == user.id,
            UserVital.vital_type == UserVitalTypeEnum.STEPS,
            UserVital.timestamp >= cutoff,
        )
        .order_by(UserVital.timestamp.asc())
        .all()
    )
    recent = _serialize_vital_series(rows, UserVitalTypeEnum.STEPS)[-STEP_STREAK_WINDOW_DAYS:]
    return [bool((item.get("value") or 0) > 0) for item in recent]


def _build_resting_hr_metric(db: Session, user: User) -> dict[str, Any]:
    previous_start, current_start, current_end = _rolling_window_bounds()
    rows = _query_vital_rows(db, user, UserVitalTypeEnum.HEART_RATE, previous_start, current_end)
    current_rows = [row for row in rows if row.timestamp and row.timestamp >= current_start]
    previous_rows = [row for row in rows if row.timestamp and row.timestamp < current_start]

    def _resting_stats(source_rows: list[UserVital]) -> tuple[float | None, list[dict[str, Any]]]:
        serialized = _serialize_vital_series(source_rows, UserVitalTypeEnum.HEART_RATE)
        values = [float(item["value"]) for item in serialized if item.get("value") is not None]
        resting_value = _percentile(values, 20.0)
        resting_band = []
        if values:
            cutoff = _percentile(values, 30.0)
            resting_band = [
                item
                for item in serialized
                if item.get("value") is not None and cutoff is not None and float(item["value"]) <= float(cutoff)
            ]
        return (round(resting_value, 1) if resting_value is not None else None, resting_band)

    current_value, current_series = _resting_stats(current_rows)
    previous_value, _previous_series = _resting_stats(previous_rows)
    delta = None if current_value is None or previous_value is None else round(current_value - previous_value, 2)
    last_updated = current_series[-1]["timestamp"] if current_series else None
    logger.info(
        "METRIC_DB_FETCH | metric_type=resting_hr | user_id=%s | window_start=%s | window_end=%s | series_length=%s | current=%s | previous=%s | source=computed_from_heart_rate",
        str(user.id),
        current_start.isoformat(),
        current_end.isoformat(),
        len(current_series),
        current_value,
        previous_value,
    )
    return {
        "value": current_value,
        "current": current_value,
        "previous": previous_value,
        "delta": delta,
        "trend": _trend_from_delta("resting_hr", delta),
        "unit": "bpm",
        "status": "ready" if current_value is not None else "no_data",
        "source": "computed_from_heart_rate_db",
        "last_updated": last_updated,
        "series": current_series,
        "window": "rolling_24h",
        "window_start": current_start.isoformat(),
        "window_end": current_end.isoformat(),
        "empty_message": None if current_value is not None else RECENT_EMPTY_MESSAGES["resting_hr"],
    }


def _build_recovery_metric(metrics: dict[str, dict[str, Any]], user: User) -> dict[str, Any]:
    sleep_metric = metrics.get("sleep") or {}
    steps_metric = metrics.get("steps") or {}
    heart_metric = metrics.get("heart_rate") or {}
    resting_metric = metrics.get("resting_hr") or {}

    sleep_value = sleep_metric.get("current")
    resting_hr = resting_metric.get("current")
    steps_value = steps_metric.get("current")
    heart_values = [float(point["value"]) for point in heart_metric.get("series", []) if point.get("value") is not None]
    current_avg_hr = round(_average(heart_values), 1) if heart_values else None
    previous_avg_hr = None
    if heart_metric.get("previous") is not None:
        previous_avg_hr = float(heart_metric["previous"])

    if sleep_value is None or resting_hr is None:
        logger.info(
            "METRIC_DB_FETCH | metric_type=recovery | user_id=%s | series_length=0 | current=None | previous=None | source=computed_from_live_metrics | status=insufficient_data",
            str(user.id),
        )
        return {
            "value": None,
            "current": None,
            "previous": None,
            "delta": None,
            "trend": "flat",
            "unit": "%",
            "status": "insufficient_data",
            "source": "computed_from_live_metrics",
            "last_updated": sleep_metric.get("last_updated") or resting_metric.get("last_updated"),
            "series": [],
            "window": "rolling_24h",
            "window_start": sleep_metric.get("window_start"),
            "window_end": sleep_metric.get("window_end"),
            "empty_message": "Insufficient live data for recovery",
            "inputs": {
                "sleep_hours": sleep_value,
                "resting_hr": resting_hr,
                "steps": steps_value,
                "avg_heart_rate": current_avg_hr,
            },
        }

    def _score_recovery(
        sleep_hours: float | None,
        resting_value: float | None,
        step_total: float | None,
        avg_heart_rate: float | None,
        avg_heart_rate_previous: float | None,
    ) -> float | None:
        if sleep_hours is None or resting_value is None:
            return None

        components: list[tuple[float, float]] = []
        sleep_component = max(0.0, min(100.0, (float(sleep_hours) / 8.0) * 100.0))
        resting_component = max(0.0, min(100.0, 100.0 - max(0.0, (float(resting_value) - 50.0) * 3.5)))
        components.extend([(sleep_component, 0.5), (resting_component, 0.35)])

        if step_total is not None:
            step_component = max(0.0, min(100.0, (float(step_total) / 8000.0) * 100.0))
            components.append((step_component, 0.1))

        if avg_heart_rate is not None and avg_heart_rate_previous is not None:
            stability = max(0.0, min(100.0, 100.0 - abs(float(avg_heart_rate) - float(avg_heart_rate_previous)) * 2.5))
            components.append((stability, 0.05))

        total_weight = sum(weight for _value, weight in components)
        if total_weight <= 0:
            return None
        return round(sum(value * weight for value, weight in components) / total_weight, 1)

    current_score = _score_recovery(sleep_value, resting_hr, steps_value, current_avg_hr, previous_avg_hr)
    previous_score = _score_recovery(
        sleep_metric.get("previous"),
        resting_metric.get("previous"),
        steps_metric.get("previous"),
        previous_avg_hr,
        None,
    )
    delta = None if current_score is None or previous_score is None else round(current_score - previous_score, 2)
    series: list[dict[str, Any]] = []
    if current_score is not None and sleep_metric.get("last_updated"):
        series.append(
            {
                "timestamp": sleep_metric["last_updated"],
                "value": current_score,
                "source": "computed_from_live_metrics",
            }
        )

    logger.info(
        "METRIC_DB_FETCH | metric_type=recovery | user_id=%s | series_length=%s | current=%s | previous=%s | source=computed_from_live_metrics | status=%s",
        str(user.id),
        len(series),
        current_score,
        previous_score,
        "ready" if current_score is not None else "insufficient_data",
    )
    return {
        "value": current_score,
        "current": current_score,
        "previous": previous_score,
        "delta": delta,
        "trend": _trend_from_delta("recovery", delta),
        "unit": "%",
        "status": "ready" if current_score is not None else "insufficient_data",
        "source": "computed_from_live_metrics",
        "last_updated": sleep_metric.get("last_updated") or resting_metric.get("last_updated"),
        "series": series,
        "window": "rolling_24h",
        "window_start": sleep_metric.get("window_start"),
        "window_end": sleep_metric.get("window_end"),
        "empty_message": None if current_score is not None else RECENT_EMPTY_MESSAGES["recovery"],
        "inputs": {
            "sleep_hours": sleep_value,
            "resting_hr": resting_hr,
            "steps": steps_value,
            "avg_heart_rate": current_avg_hr,
        },
    }


def _is_valid_blood_pressure_pair(systolic: Any, diastolic: Any) -> bool:
    try:
        if systolic is None or diastolic is None:
            return False
        return float(systolic) != float(diastolic)
    except (TypeError, ValueError):
        return False


def _coerce_blood_pressure_value(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _classify_blood_pressure_reading(systolic: Any, diastolic: Any) -> str:
    systolic_value = _coerce_blood_pressure_value(systolic)
    diastolic_value = _coerce_blood_pressure_value(diastolic)
    if systolic_value is None and diastolic_value is None:
        return "missing"
    if systolic_value is None or diastolic_value is None:
        return "partial"
    if systolic_value == diastolic_value:
        return "duplicate"
    return "pair"


def _build_blood_pressure_metric(
    systolic_payload: dict[str, Any],
    diastolic_payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    systolic_series = {
        point.get("timestamp"): _coerce_blood_pressure_value(point.get("value"))
        for point in systolic_payload.get("series", [])
        if point.get("timestamp")
    }
    diastolic_series = {
        point.get("timestamp"): _coerce_blood_pressure_value(point.get("value"))
        for point in diastolic_payload.get("series", [])
        if point.get("timestamp")
    }

    series: list[dict[str, Any]] = []
    latest_valid_pair: dict[str, Any] | None = None
    latest_partial_reading: dict[str, Any] | None = None
    for timestamp in sorted(set(systolic_series) | set(diastolic_series)):
        systolic = systolic_series.get(timestamp)
        diastolic = diastolic_series.get(timestamp)
        reading_state = _classify_blood_pressure_reading(systolic, diastolic)
        if reading_state == "missing":
            continue
        if reading_state == "duplicate":
            logger.warning(
                "BP_SKIPPED_INVALID | stage=api_response | user_id=%s | timestamp=%s | systolic=%s | diastolic=%s",
                user_id,
                timestamp,
                systolic,
                diastolic,
            )
            logger.warning(
                "BP_VALIDATION | stage=api_response | user_id=%s | timestamp=%s | status=rejected_duplicate | systolic=%s | diastolic=%s",
                user_id,
                timestamp,
                systolic,
                diastolic,
            )
            continue

        paired_point = {
            "timestamp": timestamp,
            "systolic": systolic,
            "diastolic": diastolic,
        }
        series.append(paired_point)
        logger.info(
            "BP_VALIDATION | stage=api_response | user_id=%s | timestamp=%s | status=%s | systolic=%s | diastolic=%s",
            user_id,
            timestamp,
            reading_state,
            systolic,
            diastolic,
        )
        if reading_state == "pair":
            latest_valid_pair = paired_point
        elif latest_partial_reading is None or timestamp >= latest_partial_reading["timestamp"]:
            latest_partial_reading = paired_point

    fallback_systolic = _coerce_blood_pressure_value(systolic_payload.get("value"))
    fallback_diastolic = _coerce_blood_pressure_value(diastolic_payload.get("value"))
    fallback_systolic_timestamp = systolic_payload.get("last_updated")
    fallback_diastolic_timestamp = diastolic_payload.get("last_updated")
    fallback_pair: dict[str, Any] | None = None
    fallback_partial: dict[str, Any] | None = None
    if fallback_systolic_timestamp and fallback_systolic_timestamp == fallback_diastolic_timestamp:
        fallback_state = _classify_blood_pressure_reading(fallback_systolic, fallback_diastolic)
        if fallback_state == "pair":
            fallback_pair = {
                "timestamp": fallback_systolic_timestamp,
                "systolic": fallback_systolic,
                "diastolic": fallback_diastolic,
            }
        elif fallback_state == "partial":
            fallback_partial = {
                "timestamp": fallback_systolic_timestamp,
                "systolic": fallback_systolic,
                "diastolic": fallback_diastolic,
            }
        elif fallback_systolic is not None or fallback_diastolic is not None:
            logger.warning(
                "BP_SKIPPED_INVALID | stage=api_response_latest | user_id=%s | timestamp=%s | systolic=%s | diastolic=%s",
                user_id,
                fallback_systolic_timestamp,
                fallback_systolic,
                fallback_diastolic,
            )
    else:
        partial_candidates = [
            {
                "timestamp": fallback_systolic_timestamp,
                "systolic": fallback_systolic,
                "diastolic": None,
            }
            if fallback_systolic_timestamp and fallback_systolic is not None
            else None,
            {
                "timestamp": fallback_diastolic_timestamp,
                "systolic": None,
                "diastolic": fallback_diastolic,
            }
            if fallback_diastolic_timestamp and fallback_diastolic is not None
            else None,
        ]
        fallback_partial = max(
            [candidate for candidate in partial_candidates if candidate is not None],
            key=lambda item: item["timestamp"],
            default=None,
        )

    selected_reading = latest_valid_pair or fallback_pair or latest_partial_reading or fallback_partial

    if selected_reading is not None:
        logger.info(
            "BP_API_RESPONSE | user_id=%s | timestamp=%s | systolic=%s | diastolic=%s | status=%s",
            user_id,
            selected_reading["timestamp"],
            selected_reading["systolic"],
            selected_reading["diastolic"],
            "ready" if _classify_blood_pressure_reading(selected_reading["systolic"], selected_reading["diastolic"]) == "pair" else "partial",
        )

    has_any_bp_data = bool(
        systolic_payload.get("last_updated")
        or diastolic_payload.get("last_updated")
        or systolic_payload.get("series")
        or diastolic_payload.get("series")
    )
    value = (
        {
            "systolic": selected_reading["systolic"],
            "diastolic": selected_reading["diastolic"],
        }
        if selected_reading is not None
        else None
    )
    selected_state = _classify_blood_pressure_reading(
        selected_reading["systolic"] if selected_reading is not None else None,
        selected_reading["diastolic"] if selected_reading is not None else None,
    )
    return {
        "value": value,
        "unit": "mmHg",
        "status": "ready" if selected_state == "pair" else ("partial" if selected_state == "partial" else ("missing" if has_any_bp_data else "no_data")),
        "source": systolic_payload.get("source") or diastolic_payload.get("source") or "google_fit",
        "last_updated": selected_reading["timestamp"] if selected_reading is not None else None,
        "systolic": selected_reading["systolic"] if selected_reading is not None else None,
        "diastolic": selected_reading["diastolic"] if selected_reading is not None else None,
        "series": series,
    }


def _build_temporal_blood_pressure_payload(
    db: Session,
    user: User,
    *,
    range_value: str,
    timezone_name: str,
) -> dict[str, Any]:
    bucket_starts, window_start, window_end = _bucket_grid(range_value, timezone_name)
    query_start = _expand_query_window(window_start)
    systolic_rows = _query_metric_rows(db, user, UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC, query_start, window_end)
    diastolic_rows = _query_metric_rows(db, user, UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC, query_start, window_end)
    systolic_series = _build_continuous_series(
        metric_name="blood_pressure_systolic",
        range_value=range_value,
        timezone_name=timezone_name,
        user_id=user.id,
        observed_buckets=_actual_bucket_values(systolic_rows, "blood_pressure_systolic", UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC, range_value, timezone_name),
        bucket_starts=bucket_starts,
        unit="mmHg",
    )
    diastolic_series = _build_continuous_series(
        metric_name="blood_pressure_diastolic",
        range_value=range_value,
        timezone_name=timezone_name,
        user_id=user.id,
        observed_buckets=_actual_bucket_values(diastolic_rows, "blood_pressure_diastolic", UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC, range_value, timezone_name),
        bucket_starts=bucket_starts,
        unit="mmHg",
    )
    paired_series: list[dict[str, Any]] = []
    for index, bucket_start in enumerate(bucket_starts):
        systolic_point = systolic_series[index] if index < len(systolic_series) else None
        diastolic_point = diastolic_series[index] if index < len(diastolic_series) else None
        if systolic_point is None and diastolic_point is None:
            continue
        paired_series.append(
            {
                "timestamp": (systolic_point or diastolic_point).get("timestamp"),
                "systolic": _clamp_metric_value("blood_pressure_systolic", _coerce_blood_pressure_value((systolic_point or {}).get("value"))),
                "diastolic": _clamp_metric_value("blood_pressure_diastolic", _coerce_blood_pressure_value((diastolic_point or {}).get("value"))),
                "source": (
                    "observed"
                    if (systolic_point or {}).get("source") == "observed" and (diastolic_point or {}).get("source") == "observed"
                    else ("blended" if "observed" in {(systolic_point or {}).get("source"), (diastolic_point or {}).get("source")} else "estimated")
                ),
            }
        )

    current = paired_series[-1] if paired_series else None
    previous = paired_series[-2] if len(paired_series) > 1 else None
    systolic_delta = None
    diastolic_delta = None
    if current is not None and previous is not None:
        current_systolic = _coerce_blood_pressure_value(current.get("systolic"))
        previous_systolic = _coerce_blood_pressure_value(previous.get("systolic"))
        current_diastolic = _coerce_blood_pressure_value(current.get("diastolic"))
        previous_diastolic = _coerce_blood_pressure_value(previous.get("diastolic"))
        if current_systolic is not None and previous_systolic is not None:
            systolic_delta = round(current_systolic - previous_systolic, 1)
        if current_diastolic is not None and previous_diastolic is not None:
            diastolic_delta = round(current_diastolic - previous_diastolic, 1)

    return {
        "value": {
            "systolic": current.get("systolic") if current else None,
            "diastolic": current.get("diastolic") if current else None,
        }
        if current
        else None,
        "current": {
            "systolic": current.get("systolic") if current else None,
            "diastolic": current.get("diastolic") if current else None,
        }
        if current
        else None,
        "previous": {
            "systolic": previous.get("systolic") if previous else None,
            "diastolic": previous.get("diastolic") if previous else None,
        }
        if previous
        else None,
        "delta": {
            "systolic": systolic_delta,
            "diastolic": diastolic_delta,
        }
        if systolic_delta is not None or diastolic_delta is not None
        else None,
        "trend": _trend_from_delta("blood_pressure", systolic_delta),
        "unit": "mmHg",
        "status": "ready" if current is not None else "no_data",
        "source": (
            "observed"
            if current and current.get("source") == "observed"
            else ("blended" if current and current.get("source") == "blended" else "simulated_continuity")
        ),
        "last_updated": current.get("timestamp") if current else None,
        "systolic": current.get("systolic") if current else None,
        "diastolic": current.get("diastolic") if current else None,
        "series": paired_series,
        "window": range_value,
        "window_start": paired_series[0]["timestamp"] if paired_series else None,
        "window_end": paired_series[-1]["timestamp"] if paired_series else None,
        "timezone": timezone_name,
        "bucket_count": len(paired_series),
        "empty_message": None if current is not None else RECENT_EMPTY_MESSAGES["blood_pressure"],
    }


def _build_temporal_metric_payloads(
    db: Session,
    user: User,
    *,
    range_value: str,
    timezone_name: str,
) -> dict[str, Any]:
    normalized_range = _normalize_metric_range(range_value)
    bucket_starts, window_start, window_end = _bucket_grid(normalized_range, timezone_name)
    query_start = _expand_query_window(window_start)
    metric_specs = {
        "steps": (UserVitalTypeEnum.STEPS, "count"),
        "heart_rate": (UserVitalTypeEnum.HEART_RATE, "bpm"),
        "sleep": (UserVitalTypeEnum.SLEEP, "hours"),
        "spo2": (UserVitalTypeEnum.SPO2, "%"),
        "body_temperature": (UserVitalTypeEnum.BODY_TEMPERATURE, "celsius"),
        "glucose": (UserVitalTypeEnum.GLUCOSE, "mg/dL"),
    }
    metric_rows = {
        metric_name: _query_metric_rows(db, user, vital_type, query_start, window_end)
        for metric_name, (vital_type, _unit) in metric_specs.items()
    }

    heart_rate_series = _build_continuous_series(
        metric_name="heart_rate",
        range_value=normalized_range,
        timezone_name=timezone_name,
        user_id=user.id,
        observed_buckets=_actual_bucket_values(metric_rows["heart_rate"], "heart_rate", UserVitalTypeEnum.HEART_RATE, normalized_range, timezone_name),
        bucket_starts=bucket_starts,
        unit="bpm",
    )
    spo2_series = _build_continuous_series(
        metric_name="spo2",
        range_value=normalized_range,
        timezone_name=timezone_name,
        user_id=user.id,
        observed_buckets=_actual_bucket_values(metric_rows["spo2"], "spo2", UserVitalTypeEnum.SPO2, normalized_range, timezone_name),
        bucket_starts=bucket_starts,
        unit="%",
    )
    temperature_series = _build_continuous_series(
        metric_name="body_temperature",
        range_value=normalized_range,
        timezone_name=timezone_name,
        user_id=user.id,
        observed_buckets=_actual_bucket_values(metric_rows["body_temperature"], "body_temperature", UserVitalTypeEnum.BODY_TEMPERATURE, normalized_range, timezone_name),
        bucket_starts=bucket_starts,
        unit="celsius",
    )
    glucose_series = _build_continuous_series(
        metric_name="glucose",
        range_value=normalized_range,
        timezone_name=timezone_name,
        user_id=user.id,
        observed_buckets=_actual_bucket_values(metric_rows["glucose"], "glucose", UserVitalTypeEnum.GLUCOSE, normalized_range, timezone_name),
        bucket_starts=bucket_starts,
        unit="mg/dL",
    )
    steps_series, current_steps = _build_steps_series(
        range_value=normalized_range,
        timezone_name=timezone_name,
        user_id=user.id,
        rows=metric_rows["steps"],
        bucket_starts=bucket_starts,
    )
    sleep_series, current_sleep = _build_sleep_series(
        range_value=normalized_range,
        timezone_name=timezone_name,
        user_id=user.id,
        rows=metric_rows["sleep"],
        bucket_starts=bucket_starts,
    )
    recovery_series, current_recovery = _build_recovery_series(
        range_value=normalized_range,
        timezone_name=timezone_name,
        user_id=user.id,
        bucket_starts=bucket_starts,
        sleep_series=sleep_series,
        steps_series=steps_series,
        heart_rate_series=heart_rate_series,
    )
    blood_pressure = _build_temporal_blood_pressure_payload(
        db,
        user,
        range_value=normalized_range,
        timezone_name=timezone_name,
    )
    resting_hr_series = _build_continuous_series(
        metric_name="resting_hr",
        range_value=normalized_range,
        timezone_name=timezone_name,
        user_id=user.id,
        observed_buckets=_actual_bucket_values(metric_rows["heart_rate"], "resting_hr", UserVitalTypeEnum.HEART_RATE, normalized_range, timezone_name),
        bucket_starts=bucket_starts,
        unit="bpm",
    )
    resting_hr_current = _resting_hr_from_series(heart_rate_series)
    if resting_hr_current is not None and resting_hr_series:
        resting_hr_series[-1]["value"] = resting_hr_current
        resting_hr_series[-1]["source"] = "blended"

    metrics = {
        "heart_rate": _metric_payload_from_series(
            metric_name="heart_rate",
            unit="bpm",
            range_value=normalized_range,
            timezone_name=timezone_name,
            series=heart_rate_series,
            precision=0,
        ),
        "spo2": _metric_payload_from_series(
            metric_name="spo2",
            unit="%",
            range_value=normalized_range,
            timezone_name=timezone_name,
            series=spo2_series,
            precision=1,
        ),
        "glucose": _metric_payload_from_series(
            metric_name="glucose",
            unit="mg/dL",
            range_value=normalized_range,
            timezone_name=timezone_name,
            series=glucose_series,
            precision=0,
        ),
        "body_temperature": _metric_payload_from_series(
            metric_name="body_temperature",
            unit="celsius",
            range_value=normalized_range,
            timezone_name=timezone_name,
            series=temperature_series,
            precision=1,
        ),
        "steps": _metric_payload_from_series(
            metric_name="steps",
            unit="count",
            range_value=normalized_range,
            timezone_name=timezone_name,
            series=steps_series,
            current_value=current_steps,
            precision=0,
        ),
        "sleep": _metric_payload_from_series(
            metric_name="sleep",
            unit="hours",
            range_value=normalized_range,
            timezone_name=timezone_name,
            series=sleep_series,
            current_value=current_sleep,
            precision=1,
        ),
        "recovery": _metric_payload_from_series(
            metric_name="recovery",
            unit="%",
            range_value=normalized_range,
            timezone_name=timezone_name,
            series=recovery_series,
            current_value=current_recovery,
            precision=0,
        ),
        "resting_hr": _metric_payload_from_series(
            metric_name="resting_hr",
            unit="bpm",
            range_value=normalized_range,
            timezone_name=timezone_name,
            series=resting_hr_series,
            current_value=resting_hr_current,
            precision=0,
            source_override="computed_from_heart_rate",
        ),
        "blood_pressure": blood_pressure,
    }
    metrics["steps"]["streak"] = _step_streak(db, user)
    metrics["temperature"] = {**metrics["body_temperature"]}
    metrics["glucose"]["display_value"] = metrics["glucose"]["value"]
    metrics["glucose"]["display_unit"] = metrics["glucose"]["unit"]
    metrics["glucose"]["raw_value"] = metrics["glucose"]["value"]
    metrics["glucose"]["raw_unit"] = metrics["glucose"]["unit"]
    metrics["glucose"]["normalized_value"] = metrics["glucose"]["value"]
    metrics["glucose"]["normalized_unit"] = metrics["glucose"]["unit"]

    return {
        "metrics": metrics,
        "range": normalized_range,
        "timezone": timezone_name,
        "generated_at": _now(),
        "window_start": bucket_starts[0].astimezone(timezone.utc).isoformat() if bucket_starts else None,
        "window_end": (
            (bucket_starts[-1] + (timedelta(days=1) if normalized_range == "7d" else timedelta(hours=1))).astimezone(timezone.utc).isoformat()
            if bucket_starts
            else None
        ),
        "bucket_count": len(bucket_starts),
        "day_key": datetime.now(_timezone_info(timezone_name)).date().isoformat(),
        "available_ranges": sorted(SUPPORTED_METRIC_RANGES),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Private data fetchers (swap these out for real ML calls)
# ─────────────────────────────────────────────────────────────────────────────

from integrations.rag_client import RAGClient
from pipelines.storage_pipeline.service import StoragePipelineService
from database.session import SessionLocal

# ─────────────────────────────────────────────────────────────────────────────
# Private data fetchers (delegated to integrations)
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_ml_health_score(user: User) -> Optional[dict]:
    """Reads the latest persisted health score first."""
    db = SessionLocal()
    try:
        latest = StoragePipelineService.latest_health_score(db, user)
        if latest is not None:
            return {
                "score": float(latest.score),
                "risk_component": float(latest.risk_component) if latest.risk_component is not None else None,
                "lifestyle_component": float(latest.lifestyle_component) if latest.lifestyle_component is not None else None,
                "vitals_component": float(latest.vitals_component) if latest.vitals_component is not None else None,
                "sleep_component": float(latest.sleep_component) if latest.sleep_component is not None else None,
                "health_payload": latest.health_payload or {},
                "calculated_at": latest.calculated_at.isoformat() if latest.calculated_at else None,
            }
    finally:
        db.close()
    return None


async def _fetch_wearable_history(user: User) -> Optional[dict]:
    """Reads wearable history from canonical backend-owned vitals."""
    db = SessionLocal()
    try:
        heart_rows = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.vital_type == UserVitalTypeEnum.HEART_RATE,
            )
            .order_by(UserVital.timestamp.desc())
            .limit(7)
            .all()
        )
        sleep_rows = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.vital_type == UserVitalTypeEnum.SLEEP,
            )
            .order_by(UserVital.timestamp.desc())
            .limit(7)
            .all()
        )
    finally:
        db.close()

    if not heart_rows and not sleep_rows:
        return None

    hrv = [
        {
            "time": row.timestamp.strftime("%I %p").lstrip("0") if row.timestamp else "",
            "value": round(float(row.value), 1),
        }
        for row in reversed(heart_rows)
        if row.value is not None
    ]
    sleep = [
        {
            "day": row.timestamp.strftime("%a").upper() if row.timestamp else "",
            "hours": round(float(row.value), 1),
        }
        for row in reversed(sleep_rows)
        if row.value is not None
    ]
    avg_sleep = round(sum(item["hours"] for item in sleep) / len(sleep), 1) if sleep else None
    avg_hr = round(sum(item["value"] for item in hrv) / len(hrv), 1) if hrv else None

    return {
        "hrv": hrv,
        "hrv_average_bpm": avg_hr,
        "sleep": sleep,
        "sleep_average_hours": avg_sleep,
    }


async def _fetch_ml_prediction(user: User) -> Optional[dict]:
    """Reads the latest persisted risk score first."""
    db = SessionLocal()
    try:
        latest = StoragePipelineService.latest_risk_score(db, user)
        if latest is not None:
            payload = latest.risk_payload if isinstance(latest.risk_payload, dict) else {}
            cached_explanation = payload.get("rag_explanation") if isinstance(payload.get("rag_explanation"), dict) else {}
            return {
                "prediction_id": str(latest.id),
                "risk_score": float(latest.overall_score),
                "risk_level": latest.risk_level.value if hasattr(latest.risk_level, "value") else str(latest.risk_level),
                "confidence": float(latest.confidence_score) if latest.confidence_score is not None else None,
                "drivers": payload.get("drivers", []),
                "recommendations": payload.get("recommendations", []),
                "analysis": payload.get("analysis"),
                "explanation": cached_explanation.get("payload"),
                "feature_snapshot": latest.feature_snapshot or {},
                "last_updated": latest.calculated_at.isoformat() if latest.calculated_at else None,
            }
    finally:
        db.close()
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public service methods (called by route handlers)
# ─────────────────────────────────────────────────────────────────────────────

async def get_health_score(user: User, db: Session) -> dict:
    ml_result = await _fetch_ml_health_score(user)

    if ml_result is not None:
        return _envelope(ml_result, status="ready", source="ml")

    # ── Fallback: derive score from persisted onboarding data when it exists ──
    raw_score = getattr(user, "health_score", None)

    if raw_score is None:
        return _envelope(
            {
                "score": None,
                "risk_level": None,
                "label": "No recent data",
                "change_percent": None,
            },
            status="fallback",
            source="db",
            error="No persisted health score available",
        )

    score = round(float(raw_score), 1)
    risk_level = "Low" if score >= 80 else "Moderate" if score >= 60 else "High"
    return _envelope(
        {
            "score": score,
            "risk_level": risk_level,
            "label": "Optimal" if score >= 80 else risk_level,
            "change_percent": getattr(user, "score_change_percent", 0.0) or 0.0,
        },
        status="ready",
        source="computed",
    )


async def get_health_history(user: User, db: Session) -> dict:
    previous_start, current_start, current_end = _rolling_window_bounds()
    heart_rows = _query_vital_rows(db, user, UserVitalTypeEnum.HEART_RATE, previous_start, current_end)
    sleep_rows = _query_vital_rows(db, user, UserVitalTypeEnum.SLEEP, previous_start, current_end)

    current_heart = [row for row in heart_rows if row.timestamp and row.timestamp >= current_start]
    current_sleep = [row for row in sleep_rows if row.timestamp and row.timestamp >= current_start]

    heart_series = []
    for item in _serialize_vital_series(current_heart, UserVitalTypeEnum.HEART_RATE):
        label_ts = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")) if item.get("timestamp") else None
        heart_series.append(
            {
                "time": label_ts.strftime("%I:%M %p").lstrip("0") if label_ts else "",
                "value": item["value"],
                "timestamp": item["timestamp"],
            }
        )
    sleep_series = []
    for item in _serialize_vital_series(current_sleep, UserVitalTypeEnum.SLEEP):
        label_ts = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")) if item.get("timestamp") else None
        sleep_series.append(
            {
                "day": label_ts.strftime("%a").upper() if label_ts else "",
                "hours": item["value"],
                "timestamp": item["timestamp"],
            }
        )
    avg_sleep = round(sum(item["hours"] for item in sleep_series) / len(sleep_series), 1) if sleep_series else None
    avg_hr = round(sum(item["value"] for item in heart_series) / len(heart_series), 1) if heart_series else None
    has_data = bool(heart_series or sleep_series)

    return _envelope(
        {
            "hrv": heart_series,
            "hrv_average_bpm": avg_hr,
            "sleep": sleep_series,
            "sleep_average_hours": avg_sleep,
            "window": "rolling_24h",
            "window_start": current_start.isoformat(),
            "window_end": current_end.isoformat(),
        },
        status="ready" if has_data else "fallback",
        source="wearable" if has_data else "db",
        error=None if has_data else "No recent wearable history available",
    )


async def get_latest_prediction(user: User, db: Session) -> dict:
    ml = await _fetch_ml_prediction(user)

    if ml is not None:
        return _envelope(ml, status="ready", source="ml")

    # ── Fallback: compute from stored health score ────────────────────────────
    raw_score = getattr(user, "health_score", None) or 75
    score = float(raw_score)
    risk_level = "Low" if score >= 80 else "Moderate" if score >= 60 else "High"
    bio_offset = round((score - 75) / 10, 1)
    bio_str = f"{'-' if bio_offset >= 0 else '+'}{abs(bio_offset)}y"

    return _envelope(
        {
            "risk_score": round(100 - score, 1),
            "risk_level": risk_level,
            "biological_age_delta": bio_str,
            "metabolic_rate": "High" if score >= 80 else "Moderate",
            "trajectory_percentile": min(99, max(10, int(score))),
            "recommendations": [
                "Maintain current activity level",
                "Schedule a routine check-up in 6 months",
                "Focus on consistent sleep patterns",
            ],
        },
        status="fallback",
        source="computed",
    )


async def get_user_profile(user: User, db: Session) -> dict:
    return _envelope(
        {
            "id": str(user.id),
            "full_name": user.full_name or "User",
            "email": user.email,
            "is_email_verified": user.is_email_verified,
            "onboarding_done": user.is_onboarding_done,
            "member_since": user.created_at.isoformat() if user.created_at else None,
        },
        status="ready",
        source="computed",
    )


from services.alert_service import get_active_alerts

async def get_alerts(user: User, db: Session) -> dict:
    """
    Returns dynamic alerts list via alert_service.
    """
    return await get_active_alerts(user, db)


async def get_recommended_tests(user: User, db: Session) -> dict:
    recommendations = generate_test_recommendations(user.id, db=db)
    status = "ready" if recommendations else "fallback"
    return _envelope(recommendations, status=status, source="clinical_recommendation_engine")


async def get_recommendation_plan(user: User, db: Session) -> dict:
    from services.orchestrator import OrchestratorRequest, get_orchestrator

    orchestrated = await get_orchestrator().run(
        OrchestratorRequest(
            workflow="recommendations",
            user_id=str(user.id),
            db=db,
            current_user=user,
            endpoint_type="dashboard_recommendations",
            intent="recommendations",
            latency_tier="interactive",
        )
    )
    payload = orchestrated.get("data") if isinstance(orchestrated.get("data"), dict) else {}
    plan = payload.get("plan")
    status = "ready" if plan else "fallback"
    return _envelope(plan, status=status, source="ai_orchestrator")


async def get_health_metrics(
    user: User,
    db: Session,
    *,
    range_value: str = "24h",
    timezone_name: str | None = None,
) -> dict:
    resolved_range = _normalize_metric_range(range_value)
    resolved_timezone = _resolve_timezone_name(db, user, timezone_name)
    payload = _build_temporal_metric_payloads(
        db,
        user,
        range_value=resolved_range,
        timezone_name=resolved_timezone,
    )
    metrics = payload.get("metrics", {})

    latest_location = (
        db.query(WearableMetric)
        .filter(WearableMetric.user_id == user.id, WearableMetric.metric_type == "location")
        .order_by(WearableMetric.timestamp.desc())
        .first()
    )
    if latest_location is not None:
        metrics["location"] = {
            "value": latest_location.value,
            "unit": latest_location.unit,
            "status": "ready",
            "source": latest_location.source,
            "last_updated": latest_location.timestamp.isoformat() if latest_location.timestamp else None,
            "metadata": latest_location.metric_metadata or {},
        }

    latest_health = StoragePipelineService.latest_health_score(db, user)
    if latest_health is not None:
        health_payload = latest_health.health_payload or {}
        metrics["health_score"] = {
            "value": float(latest_health.score),
            "unit": "score",
            "status": "ready",
            "source": latest_health.source,
            "last_updated": latest_health.calculated_at.isoformat() if latest_health.calculated_at else None,
            "components": health_payload,
        }

    latest_metric_update = max(
        [
            metric.get("last_updated")
            for metric in metrics.values()
            if isinstance(metric, dict) and metric.get("last_updated")
        ],
        default=payload.get("generated_at"),
    )
    has_data = any(
        isinstance(metric, dict) and metric.get("status") in {"ready", "partial"}
        for metric in metrics.values()
    )

    for metric_name, metric_payload in metrics.items():
        if not isinstance(metric_payload, dict):
            continue
        logger.info(
            "METRIC_API_RESPONSE | metric_type=%s | user_id=%s | range=%s | timezone=%s | status=%s | series_length=%s | last_updated=%s | source=%s",
            metric_name,
            str(user.id),
            resolved_range,
            resolved_timezone,
            metric_payload.get("status"),
            len(metric_payload.get("series", []) if isinstance(metric_payload.get("series"), list) else []),
            metric_payload.get("last_updated"),
            metric_payload.get("source"),
        )

    envelope = _envelope(
        {
            "metrics": metrics,
            **metrics,
            "range": payload.get("range"),
            "timezone": payload.get("timezone"),
            "generated_at": payload.get("generated_at"),
            "window_start": payload.get("window_start"),
            "window_end": payload.get("window_end"),
            "bucket_count": payload.get("bucket_count"),
            "day_key": payload.get("day_key"),
            "available_ranges": payload.get("available_ranges"),
        },
        status="ready" if has_data else "fallback",
        source="health_metrics",
        error=None if has_data else "No health metrics available yet",
    )
    envelope["last_updated"] = latest_metric_update or _now()
    return envelope
