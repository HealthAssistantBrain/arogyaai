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
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import User, UserVital, UserVitalTypeEnum, WearableMetric
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


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    plan = generate_recommendation_plan(user.id, db=db)
    status = "ready" if plan else "fallback"
    return _envelope(plan, status=status, source="recommendation_plan_engine")


async def get_health_metrics(user: User, db: Session) -> dict:
    metric_specs = {
        "steps": (UserVitalTypeEnum.STEPS, "count"),
        "heart_rate": (UserVitalTypeEnum.HEART_RATE, "bpm"),
        "sleep": (UserVitalTypeEnum.SLEEP, "hours"),
        "spo2": (UserVitalTypeEnum.SPO2, "%"),
        "body_temperature": (UserVitalTypeEnum.BODY_TEMPERATURE, "celsius"),
    }

    metrics = {
        metric_name: _build_metric_payload(db, user, metric_name, vital_type, unit)
        for metric_name, (vital_type, unit) in metric_specs.items()
    }
    metrics["glucose"] = _build_glucose_metric_payload(db, user)
    metrics["temperature"] = metrics["body_temperature"]
    metrics["steps"]["streak"] = _step_streak(db, user)

    systolic = _build_metric_payload(db, user, "blood_pressure_systolic", UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC, "mmHg")
    diastolic = _build_metric_payload(db, user, "blood_pressure_diastolic", UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC, "mmHg")
    logger.info(
        "BP_DB_FETCH | user_id=%s | systolic=%s | diastolic=%s",
        str(user.id),
        systolic["value"],
        diastolic["value"],
    )
    metrics["blood_pressure"] = _build_blood_pressure_metric(
        systolic,
        diastolic,
        user_id=str(user.id),
    )
    metrics["blood_pressure"]["current"] = metrics["blood_pressure"]["value"]
    metrics["blood_pressure"]["previous"] = (
        {
            "systolic": systolic.get("previous"),
            "diastolic": diastolic.get("previous"),
        }
        if systolic.get("previous") is not None or diastolic.get("previous") is not None
        else None
    )
    current_bp = metrics["blood_pressure"]["value"] or {}
    if metrics["blood_pressure"]["previous"] is not None and current_bp:
        metrics["blood_pressure"]["delta"] = {
            "systolic": round(float(current_bp.get("systolic") or 0) - float(metrics["blood_pressure"]["previous"]["systolic"] or 0), 1),
            "diastolic": round(float(current_bp.get("diastolic") or 0) - float(metrics["blood_pressure"]["previous"]["diastolic"] or 0), 1),
        }
        metrics["blood_pressure"]["trend"] = _trend_from_delta(
            "blood_pressure",
            float(metrics["blood_pressure"]["delta"]["systolic"]),
        )
    else:
        metrics["blood_pressure"]["delta"] = None
        metrics["blood_pressure"]["trend"] = "flat"
    metrics["blood_pressure"]["empty_message"] = None if metrics["blood_pressure"]["value"] else RECENT_EMPTY_MESSAGES["blood_pressure"]
    metrics["blood_pressure"]["window"] = "rolling_24h"
    logger.info(
        "BP_API_RESPONSE | user_id=%s | systolic=%s | diastolic=%s | status=%s",
        str(user.id),
        metrics["blood_pressure"]["systolic"],
        metrics["blood_pressure"]["diastolic"],
        metrics["blood_pressure"]["status"],
    )

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

    metrics["resting_hr"] = _build_resting_hr_metric(db, user)
    metrics["recovery"] = _build_recovery_metric(metrics, user)

    latest_health = StoragePipelineService.latest_health_score(db, user)
    last_updated = None

    if latest_health is not None:
        payload = latest_health.health_payload or {}
        metrics["health_score"] = {
            "value": float(latest_health.score),
            "unit": "score",
            "status": "ready",
            "source": latest_health.source,
            "last_updated": latest_health.calculated_at.isoformat() if latest_health.calculated_at else None,
            "components": payload,
        }
        if latest_health.calculated_at:
            last_updated = latest_health.calculated_at.isoformat()

    latest_metric_update = max(
        [
            metric.get("last_updated")
            for metric in metrics.values()
            if isinstance(metric, dict) and metric.get("last_updated")
        ],
        default=None,
    )
    last_updated = latest_metric_update or last_updated
    has_data = any(
        isinstance(metric, dict) and metric.get("status") in {"ready", "partial"}
        for metric in metrics.values()
    )

    for metric_name, metric_payload in metrics.items():
        if not isinstance(metric_payload, dict):
            continue
        logger.info(
            "METRIC_API_RESPONSE | metric_type=%s | user_id=%s | status=%s | series_length=%s | last_updated=%s | source=%s",
            metric_name,
            str(user.id),
            metric_payload.get("status"),
            len(metric_payload.get("series", []) if isinstance(metric_payload.get("series"), list) else []),
            metric_payload.get("last_updated"),
            metric_payload.get("source"),
        )

    return _envelope(
        {"metrics": metrics, **metrics},
        status="ready" if has_data else "fallback",
        source="health_metrics",
        error=None if has_data else "No health metrics available yet",
    ) | {"last_updated": last_updated or _now()}
