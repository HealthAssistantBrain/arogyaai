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
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import User, UserVital, UserVitalTypeEnum, WearableMetric
from services.recommendation_engine import generate_recommendation_plan
from services.recommendation_service import generate_test_recommendations

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_rng(user: User) -> random.Random:
    """Deterministic RNG seeded by user.id — same user always gets same data."""
    seed = int(str(user.id).replace("-", ""), 16) % (2 ** 32)
    return random.Random(seed)


def _envelope(data: dict, status: str, source: str, error: Optional[str] = None) -> dict:
    return {
        "success": error is None,
        "status": status,          # "ready" | "processing" | "fallback"
        "source": source,          # "ml" | "wearable" | "computed" | "mock"
        "data": data,
        "error": error,
        "last_updated": _now(),
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

    # ── Fallback: derive score from persisted onboarding data ─────────────────
    raw_score = getattr(user, "health_score", None)

    if raw_score is None:
        # No onboarding data yet — return neutral defaults
        return _envelope(
            {
                "score": 75,
                "risk_level": "Moderate",
                "label": "Moderate",
                "change_percent": 0.0,
            },
            status="fallback",
            source="mock",
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
    wearable = await _fetch_wearable_history(user)

    if wearable is not None:
        return _envelope(wearable, status="ready", source="wearable")

    # ── Fallback: deterministic per-user synthetic history ────────────────────
    rng = _user_rng(user)
    time_labels = ["12 AM", "4 AM", "8 AM", "12 PM", "4 PM", "8 PM", "11 PM"]
    base_values = [80, 60, 75, 40, 65, 30, 35]
    hrv = [
        {"time": lbl, "value": max(20, min(100, base + rng.randint(-5, 5)))}
        for lbl, base in zip(time_labels, base_values)
    ]
    sleep_days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    sleep = [{"day": d, "hours": round(rng.uniform(4.0, 9.0), 1)} for d in sleep_days]
    avg_sleep = round(sum(s["hours"] for s in sleep) / len(sleep), 1)

    return _envelope(
        {
            "hrv": hrv,
            "hrv_average_bpm": rng.randint(65, 85),
            "sleep": sleep,
            "sleep_average_hours": avg_sleep,
        },
        status="fallback",
        source="mock",
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
    latest_feature = StoragePipelineService.latest_feature_snapshot(db, user)
    latest_health = StoragePipelineService.latest_health_score(db, user)

    metric_specs = {
        "steps": (UserVitalTypeEnum.STEPS, "count"),
        "heart_rate": (UserVitalTypeEnum.HEART_RATE, "bpm"),
        "sleep": (UserVitalTypeEnum.SLEEP, "hours"),
        "spo2": (UserVitalTypeEnum.SPO2, "%"),
        "glucose": (UserVitalTypeEnum.GLUCOSE, "mg/dL"),
        "body_temperature": (UserVitalTypeEnum.BODY_TEMPERATURE, "celsius"),
    }

    def _normalize_metric_value(vital_type: UserVitalTypeEnum, value: float | None, unit: str | None) -> tuple[float | None, str | None]:
        if value is None:
            return None, unit

        if vital_type == UserVitalTypeEnum.GLUCOSE and unit and unit.strip().lower() in {"mmol/l", "mmol"}:
            return round(float(value) * 18.0182, 1), "mg/dL"

        return float(value), unit

    def _metric_payload(vital_type: UserVitalTypeEnum, default_unit: str) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        latest = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.vital_type == vital_type,
            )
            .order_by(UserVital.timestamp.desc())
            .first()
        )
        rows = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.vital_type == vital_type,
                UserVital.timestamp >= cutoff,
            )
            .order_by(UserVital.timestamp.asc())
            .limit(100)
            .all()
        )
        latest_value, latest_unit = _normalize_metric_value(
            vital_type,
            float(latest.value) if latest and latest.value is not None else None,
            latest.unit if latest else default_unit,
        )
        return {
            "value": latest_value,
            "unit": latest_unit or default_unit,
            "status": "ready" if latest else "no_data",
            "source": latest.source.value if latest and latest.source else "google_fit",
            "last_updated": latest.timestamp.isoformat() if latest and latest.timestamp else None,
            "series": [
                {
                    "value": _normalize_metric_value(vital_type, float(row.value), row.unit)[0],
                    "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                }
                for row in rows
                if row.value is not None
            ],
        }

    metrics = {
        metric_name: _metric_payload(vital_type, unit)
        for metric_name, (vital_type, unit) in metric_specs.items()
    }
    metrics["temperature"] = metrics["body_temperature"]

    systolic = _metric_payload(UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC, "mmHg")
    diastolic = _metric_payload(UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC, "mmHg")
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

    last_updated = None

    if latest_feature is not None:
        metrics["resting_hr"] = {
            "value": float(latest_feature.feature_payload.get("avg_rhr")) if latest_feature.feature_payload and latest_feature.feature_payload.get("avg_rhr") is not None else None,
            "unit": "bpm",
            "status": "ready",
            "source": "feature_snapshot",
            "last_updated": latest_feature.calculated_at.isoformat() if latest_feature.calculated_at else None,
        }
        last_updated = latest_feature.calculated_at.isoformat() if latest_feature.calculated_at else last_updated

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
        isinstance(metric, dict) and metric.get("status") == "ready"
        for metric in metrics.values()
    )

    return _envelope(
        {"metrics": metrics, **metrics},
        status="ready" if has_data else "fallback",
        source="health_metrics",
        error=None if has_data else "No health metrics available yet",
    ) | {"last_updated": last_updated or _now()}
