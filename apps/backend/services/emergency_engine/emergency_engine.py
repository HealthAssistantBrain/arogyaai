from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from database.session import SessionLocal
from models import (
    Alert,
    ChatSession,
    ClinicalHistory,
    GoogleFitConnection,
    LabResult,
    Notification,
    NotificationSeverityEnum,
    NotificationTypeEnum,
    RiskScore,
    SeverityEnum,
    User,
    UserVital,
    UserVitalTypeEnum,
    WearableData,
)
from pipelines.ingestion_pipeline.service import compute_daily_steps
from services import notification_service

logger = logging.getLogger("emergency_engine")


def _int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


HIGH_RESTING_HR_THRESHOLD = 120.0
LOW_HR_THRESHOLD = 40.0
ML_CRITICAL_THRESHOLD = 0.85
FUSION_CRITICAL_THRESHOLD = 0.72
RATE_LIMIT_MINUTES = _int_env("EMERGENCY_ALERT_RATE_LIMIT_MINUTES", 15, minimum=1, maximum=240)

SIGNAL_WEIGHTS = {
    "heart_rate": 0.30,
    "activity": 0.15,
    "sleep": 0.10,
    "ml_risk": 0.25,
    "symptoms": 0.15,
    "labs": 0.05,
}

ABNORMAL_LAB_STATUSES = {"high", "low", "abnormal", "critical"}
CHEST_PAIN_TERMS = {"chest pain", "chest pressure", "chest tightness", "chest discomfort"}
FAINTING_TERMS = {"fainting", "fainted", "syncope", "passed out", "loss of consciousness"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_user_uuid(user_id: Any) -> uuid.UUID | None:
    try:
        return user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _normalize_risk_score(value: Any) -> float | None:
    score = _safe_float(value)
    if score is None:
        return None
    if score > 1.0 and score <= 100.0:
        return score / 100.0
    return max(0.0, score)


def _sleep_minutes(value: Any, unit: Any = None) -> float | None:
    minutes = _safe_float(value)
    if minutes is None:
        return None
    normalized_unit = str(unit or "").strip().lower()
    if normalized_unit in {"hour", "hours", "hr", "hrs"}:
        return minutes * 60.0
    return minutes


def _clean_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, (list, tuple, set)):
        candidates = list(value)
    else:
        candidates = [value]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)
    return normalized


def _contains_any(text: str, terms: set[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in sorted(terms) if term in lowered]


def _load_user(db: Session, user_id: uuid.UUID) -> User | None:
    return db.query(User).filter(User.id == user_id, User.is_deleted == False).first()


def _latest_vital(db: Session, user_id: uuid.UUID, vital_type: UserVitalTypeEnum) -> UserVital | None:
    return (
        db.query(UserVital)
        .filter(UserVital.user_id == user_id, UserVital.vital_type == vital_type)
        .order_by(UserVital.timestamp.desc())
        .first()
    )


def _recent_vitals(
    db: Session,
    user_id: uuid.UUID,
    vital_type: UserVitalTypeEnum,
    *,
    limit: int = 8,
) -> list[UserVital]:
    return (
        db.query(UserVital)
        .filter(UserVital.user_id == user_id, UserVital.vital_type == vital_type)
        .order_by(UserVital.timestamp.desc())
        .limit(limit)
        .all()
    )


def _collect_heart_rate(db: Session, user_id: uuid.UUID, missing: list[str]) -> dict[str, Any]:
    try:
        row = _latest_vital(db, user_id, UserVitalTypeEnum.HEART_RATE)
    except Exception as exc:
        logger.exception("[Emergency] Failed to load heart-rate signal for user=%s: %s", user_id, exc)
        missing.append("heart_rate")
        return {"value": None, "timestamp": None, "unit": "bpm", "source": None, "at_rest": None}

    if row is None:
        missing.append("heart_rate")
        return {"value": None, "timestamp": None, "unit": "bpm", "source": None, "at_rest": None}

    return {
        "value": _safe_float(row.value),
        "timestamp": _iso(row.timestamp),
        "unit": row.unit or "bpm",
        "source": getattr(row.source, "value", row.source),
        "at_rest": None,
    }


def _collect_activity(db: Session, user_id: uuid.UUID, missing: list[str]) -> dict[str, Any]:
    try:
        step_rows = _recent_vitals(db, user_id, UserVitalTypeEnum.STEPS, limit=8)
    except Exception as exc:
        logger.exception("[Emergency] Failed to load activity signal for user=%s: %s", user_id, exc)
        missing.append("activity")
        step_rows = []

    connection = db.query(GoogleFitConnection).filter(GoogleFitConnection.user_id == user_id).first()
    timezone_name = str(getattr(connection, "default_timezone", None) or "UTC")
    daily_steps = compute_daily_steps(step_rows, timezone_name)
    values = [float(item["steps"]) for item in daily_steps]

    if not values:
        if "activity" not in missing:
            missing.append("activity")
        return {
            "latest_steps": None,
            "previous_average_steps": None,
            "drop_ratio": None,
            "sudden_drop": False,
            "at_rest": None,
        }

    latest_steps = values[0]
    previous = values[1:5]
    previous_average = sum(previous) / len(previous) if previous else None
    drop_ratio = None
    sudden_drop = False
    if previous_average and previous_average >= 1000:
        drop_ratio = max(0.0, min(1.0, 1.0 - (latest_steps / previous_average)))
        sudden_drop = latest_steps <= max(500.0, previous_average * 0.4)

    latest_timestamp = step_rows[0].timestamp if step_rows else None
    at_rest = None
    if latest_timestamp:
        is_recent = latest_timestamp >= _utc_now() - timedelta(minutes=20)
        if is_recent and latest_steps <= 25:
            at_rest = True
        elif is_recent and latest_steps > 75:
            at_rest = False

    return {
        "latest_steps": latest_steps,
        "previous_average_steps": previous_average,
        "drop_ratio": drop_ratio,
        "sudden_drop": sudden_drop,
        "at_rest": at_rest,
    }


def _collect_sleep(db: Session, user_id: uuid.UUID, missing: list[str]) -> dict[str, Any]:
    try:
        row = _latest_vital(db, user_id, UserVitalTypeEnum.SLEEP)
    except Exception as exc:
        logger.exception("[Emergency] Failed to load sleep signal for user=%s: %s", user_id, exc)
        missing.append("sleep")
        return {"latest_minutes": None, "anomaly": False, "timestamp": None}

    minutes = _sleep_minutes(getattr(row, "value", None), getattr(row, "unit", None)) if row else None
    if minutes is None:
        try:
            legacy = (
                db.query(WearableData)
                .filter(WearableData.user_id == user_id, WearableData.sleep_duration_minutes.isnot(None))
                .order_by(WearableData.recorded_at.desc())
                .first()
            )
            minutes = _sleep_minutes(getattr(legacy, "sleep_duration_minutes", None), "minutes") if legacy else None
        except Exception as exc:
            logger.exception("[Emergency] Failed to load legacy sleep signal for user=%s: %s", user_id, exc)

    if minutes is None:
        missing.append("sleep")
        return {"latest_minutes": None, "anomaly": False, "timestamp": None}

    return {
        "latest_minutes": minutes,
        "anomaly": minutes < 240.0 or minutes > 720.0,
        "timestamp": _iso(getattr(row, "timestamp", None)) if row else None,
    }


def _collect_ml_risk(db: Session, user_id: uuid.UUID, missing: list[str]) -> dict[str, Any]:
    try:
        row = (
            db.query(RiskScore)
            .filter(RiskScore.user_id == user_id)
            .order_by(RiskScore.calculated_at.desc(), RiskScore.created_at.desc())
            .first()
        )
    except Exception as exc:
        logger.exception("[Emergency] Failed to load ML risk signal for user=%s: %s", user_id, exc)
        missing.append("ml_risk")
        return {"risk_score": None, "risk_level": None, "timestamp": None}

    if row is None:
        missing.append("ml_risk")
        return {"risk_score": None, "risk_level": None, "timestamp": None}

    return {
        "risk_score": _normalize_risk_score(row.overall_score),
        "raw_score": _safe_float(row.overall_score),
        "risk_level": getattr(row.risk_level, "value", row.risk_level),
        "timestamp": _iso(row.calculated_at or row.created_at),
    }


def _collect_symptoms(db: Session, user_id: uuid.UUID, missing: list[str]) -> dict[str, Any]:
    symptoms: list[str] = []
    severity: int | None = None
    latest_created_at = None

    try:
        history = (
            db.query(ClinicalHistory)
            .filter(ClinicalHistory.user_id == user_id)
            .order_by(ClinicalHistory.created_at.desc())
            .first()
        )
        if history:
            symptoms.extend(_clean_text_list(history.chief_complaint))
            symptoms.extend(_clean_text_list(history.associated_symptoms))
            severity = history.severity
            latest_created_at = history.created_at
    except Exception as exc:
        logger.exception("[Emergency] Failed to load clinical symptoms for user=%s: %s", user_id, exc)

    try:
        chat_session = db.query(ChatSession).filter(ChatSession.user_id == user_id).first()
        if chat_session:
            symptoms.extend(_clean_text_list(chat_session.symptoms_history))
    except Exception as exc:
        logger.exception("[Emergency] Failed to load chat symptoms for user=%s: %s", user_id, exc)

    symptoms = _clean_text_list(symptoms)
    if not symptoms:
        missing.append("symptoms")

    combined = " ".join(symptoms)
    chest_flags = _contains_any(combined, CHEST_PAIN_TERMS)
    fainting_flags = _contains_any(combined, FAINTING_TERMS)
    red_flags = chest_flags + fainting_flags

    return {
        "items": symptoms,
        "severity": severity,
        "red_flags": red_flags,
        "has_chest_pain": bool(chest_flags),
        "has_fainting": bool(fainting_flags),
        "timestamp": _iso(latest_created_at),
    }


def _collect_labs(db: Session, user_id: uuid.UUID, missing: list[str]) -> dict[str, Any]:
    try:
        rows = (
            db.query(LabResult)
            .filter(LabResult.user_id == user_id)
            .order_by(LabResult.timestamp.desc())
            .limit(20)
            .all()
        )
    except Exception as exc:
        logger.exception("[Emergency] Failed to load lab signals for user=%s: %s", user_id, exc)
        missing.append("labs")
        return {"abnormal": [], "critical_count": 0}

    latest_by_name: dict[str, LabResult] = {}
    for row in rows:
        if row.name and row.name not in latest_by_name:
            latest_by_name[row.name] = row

    abnormal = []
    for row in latest_by_name.values():
        status = str(row.status or "").strip().lower()
        if status in ABNORMAL_LAB_STATUSES:
            abnormal.append(
                {
                    "name": row.name,
                    "value": row.value,
                    "unit": row.unit,
                    "status": status,
                    "timestamp": _iso(row.timestamp),
                }
            )

    if not rows:
        missing.append("labs")

    return {
        "abnormal": abnormal[:6],
        "critical_count": sum(1 for item in abnormal if item.get("status") == "critical"),
    }


def _collect_signals(db: Session, user_id: uuid.UUID) -> dict[str, Any]:
    missing: list[str] = []
    activity = _collect_activity(db, user_id, missing)
    heart_rate = _collect_heart_rate(db, user_id, missing)
    heart_rate["at_rest"] = activity.get("at_rest")

    return {
        "heart_rate": heart_rate,
        "activity": activity,
        "sleep": _collect_sleep(db, user_id, missing),
        "ml": _collect_ml_risk(db, user_id, missing),
        "symptoms": _collect_symptoms(db, user_id, missing),
        "labs": _collect_labs(db, user_id, missing),
        "missing": sorted(set(missing)),
    }


def _apply_overrides(signals: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(overrides, dict) or not overrides:
        return signals

    payload = overrides.get("signals") if isinstance(overrides.get("signals"), dict) else overrides

    heart_rate = _safe_float(payload.get("heart_rate", payload.get("hr")))
    if heart_rate is not None:
        signals["heart_rate"].update({"value": heart_rate, "unit": "bpm", "source": "override"})
        signals["missing"] = [item for item in signals["missing"] if item != "heart_rate"]

    if "at_rest" in payload or "is_resting" in payload:
        signals["heart_rate"]["at_rest"] = bool(payload.get("at_rest", payload.get("is_resting")))
        signals["activity"]["at_rest"] = signals["heart_rate"]["at_rest"]

    if "activity_drop" in payload:
        signals["activity"]["sudden_drop"] = bool(payload.get("activity_drop"))
        signals["missing"] = [item for item in signals["missing"] if item != "activity"]
    if "steps" in payload:
        signals["activity"]["latest_steps"] = _safe_float(payload.get("steps"))
        signals["missing"] = [item for item in signals["missing"] if item != "activity"]
    if "previous_average_steps" in payload:
        signals["activity"]["previous_average_steps"] = _safe_float(payload.get("previous_average_steps"))
        signals["missing"] = [item for item in signals["missing"] if item != "activity"]

    sleep_minutes = _safe_float(payload.get("sleep_minutes"))
    if sleep_minutes is None:
        sleep_hours = _safe_float(payload.get("sleep_hours"))
        sleep_minutes = sleep_hours * 60.0 if sleep_hours is not None else None
    if sleep_minutes is not None:
        signals["sleep"].update(
            {
                "latest_minutes": sleep_minutes,
                "anomaly": sleep_minutes < 240.0 or sleep_minutes > 720.0,
            }
        )
        signals["missing"] = [item for item in signals["missing"] if item != "sleep"]
    if "sleep_anomaly" in payload:
        signals["sleep"]["anomaly"] = bool(payload.get("sleep_anomaly"))

    risk_score = _normalize_risk_score(payload.get("ml_risk_score", payload.get("risk_score")))
    if risk_score is not None:
        signals["ml"].update({"risk_score": risk_score, "raw_score": payload.get("ml_risk_score", payload.get("risk_score"))})
        signals["missing"] = [item for item in signals["missing"] if item != "ml_risk"]

    if "symptoms" in payload:
        items = _clean_text_list(payload.get("symptoms"))
        combined = " ".join(items)
        chest_flags = _contains_any(combined, CHEST_PAIN_TERMS)
        fainting_flags = _contains_any(combined, FAINTING_TERMS)
        signals["symptoms"].update(
            {
                "items": items,
                "red_flags": chest_flags + fainting_flags,
                "has_chest_pain": bool(chest_flags),
                "has_fainting": bool(fainting_flags),
            }
        )
        signals["missing"] = [item for item in signals["missing"] if item != "symptoms"]

    if "lab_abnormalities" in payload or "labs" in payload:
        raw_labs = payload.get("lab_abnormalities", payload.get("labs"))
        lab_items = raw_labs if isinstance(raw_labs, list) else _clean_text_list(raw_labs)
        abnormal = []
        for item in lab_items:
            if isinstance(item, dict):
                abnormal.append(item)
            else:
                abnormal.append({"name": str(item), "status": "abnormal"})
        signals["labs"].update(
            {
                "abnormal": abnormal,
                "critical_count": sum(1 for item in abnormal if str(item.get("status")).lower() == "critical"),
            }
        )
        signals["missing"] = [item for item in signals["missing"] if item != "labs"]

    return signals


def _score_signals(signals: dict[str, Any]) -> dict[str, Any]:
    scores: dict[str, float] = {}
    triggers: list[str] = []
    evidence: list[str] = []

    hr = _safe_float(signals.get("heart_rate", {}).get("value"))
    at_rest = signals.get("heart_rate", {}).get("at_rest")
    if hr is not None:
        if hr < LOW_HR_THRESHOLD:
            scores["heart_rate"] = 1.0
            triggers.append("HR < 40")
            evidence.append(f"Heart rate is critically low at {hr:.0f} bpm.")
        elif hr > HIGH_RESTING_HR_THRESHOLD and at_rest is not False:
            scores["heart_rate"] = 1.0 if hr >= 140 else 0.92
            triggers.append("HR > 120 at rest")
            rest_text = "at rest" if at_rest is True else "with no recent activity context"
            evidence.append(f"Heart rate is {hr:.0f} bpm {rest_text}.")
        elif hr > HIGH_RESTING_HR_THRESHOLD:
            scores["heart_rate"] = 0.70
            evidence.append(f"Heart rate is high at {hr:.0f} bpm while activity is present.")
        elif hr > 105:
            scores["heart_rate"] = 0.45
            evidence.append(f"Heart rate is elevated at {hr:.0f} bpm.")

    activity = signals.get("activity", {})
    if activity.get("sudden_drop"):
        scores["activity"] = 0.95
        triggers.append("sudden drop in activity")
        evidence.append("Recent activity dropped sharply compared with previous baseline.")
    elif _safe_float(activity.get("drop_ratio")) is not None:
        drop_ratio = _safe_float(activity.get("drop_ratio")) or 0.0
        if drop_ratio >= 0.4:
            scores["activity"] = 0.55
            evidence.append("Recent activity is meaningfully below baseline.")

    sleep = signals.get("sleep", {})
    sleep_minutes = _safe_float(sleep.get("latest_minutes"))
    if sleep.get("anomaly") and sleep_minutes is not None:
        if sleep_minutes < 180 or sleep_minutes > 840:
            scores["sleep"] = 0.75
        else:
            scores["sleep"] = 0.50
        evidence.append("Sleep pattern is outside the expected range.")

    ml_risk = _safe_float(signals.get("ml", {}).get("risk_score"))
    if ml_risk is not None:
        scores["ml_risk"] = min(1.0, max(0.0, ml_risk))
        if ml_risk > ML_CRITICAL_THRESHOLD:
            triggers.append("ML risk > 0.85")
            evidence.append(f"Recent health risk signal is {ml_risk:.2f}.")

    symptoms = signals.get("symptoms", {})
    if symptoms.get("has_chest_pain") or symptoms.get("has_fainting"):
        scores["symptoms"] = 1.0
        triggers.append("chest pain / fainting")
        evidence.append("Red-flag symptom history includes chest pain or fainting.")
    elif symptoms.get("items"):
        severity = _safe_float(symptoms.get("severity"))
        scores["symptoms"] = min(0.7, max(0.35, (severity or 4.0) / 10.0))

    labs = signals.get("labs", {})
    abnormal_labs = labs.get("abnormal") if isinstance(labs.get("abnormal"), list) else []
    if labs.get("critical_count"):
        scores["labs"] = 0.85
        evidence.append("Critical lab abnormality is present.")
    elif abnormal_labs:
        scores["labs"] = min(0.70, 0.35 + (len(abnormal_labs) * 0.08))
        evidence.append("Recent abnormal lab values are present.")

    active_weights = sum(SIGNAL_WEIGHTS[key] for key in scores if key in SIGNAL_WEIGHTS)
    weighted_total = sum(scores[key] * SIGNAL_WEIGHTS[key] for key in scores if key in SIGNAL_WEIGHTS)
    weighted_score = weighted_total / active_weights if active_weights else 0.0
    active_signal_count = sum(1 for score in scores.values() if score >= 0.5)
    fusion_triggered = active_signal_count >= 2 and weighted_score >= FUSION_CRITICAL_THRESHOLD
    if fusion_triggered:
        triggers.append("multi-signal fusion")
        evidence.append("Wearable, ML, symptom, or lab signals combine into a critical pattern.")

    critical_triggered = bool(triggers)
    max_signal_score = max(scores.values()) if scores else 0.0
    confidence = max(weighted_score, max_signal_score if critical_triggered else 0.0)
    if critical_triggered:
        confidence = max(confidence, 0.91)
    confidence = min(0.99, confidence)

    return {
        "scores": {key: round(value, 4) for key, value in scores.items()},
        "weighted_score": round(weighted_score, 4),
        "active_signal_count": active_signal_count,
        "triggers": list(dict.fromkeys(triggers)),
        "evidence": evidence,
        "critical": critical_triggered,
        "confidence": round(confidence, 2),
    }


def _select_event(score_result: dict[str, Any]) -> str:
    triggers = set(score_result.get("triggers") or [])
    if "HR < 40" in triggers:
        return "Possible bradycardia"
    if "HR > 120 at rest" in triggers or "chest pain / fainting" in triggers:
        return "Possible cardiac stress"
    if "ML risk > 0.85" in triggers:
        return "High predicted acute health risk"
    if "sudden drop in activity" in triggers:
        return "Sudden activity collapse"
    if "multi-signal fusion" in triggers:
        return "Multi-signal emergency pattern"
    return "No emergency detected"


def _recent_critical_alert(db: Session, user_id: uuid.UUID) -> Any | None:
    threshold = _utc_now() - timedelta(minutes=RATE_LIMIT_MINUTES)

    notification = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.notification_type == NotificationTypeEnum.HEALTH_ALERT,
            Notification.severity == NotificationSeverityEnum.CRITICAL,
            Notification.created_at >= threshold,
        )
        .order_by(Notification.created_at.desc())
        .first()
    )
    if notification is not None:
        return notification

    return (
        db.query(Alert)
        .filter(
            Alert.user_id == user_id,
            Alert.severity == SeverityEnum.CRITICAL,
            Alert.created_at >= threshold,
        )
        .order_by(Alert.created_at.desc())
        .first()
    )


def _next_alert_after(recent_alert: Any | None) -> str | None:
    created_at = getattr(recent_alert, "created_at", None)
    if not isinstance(created_at, datetime):
        return None
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (created_at + timedelta(minutes=RATE_LIMIT_MINUTES)).isoformat()


def _build_state(
    *,
    user_id: uuid.UUID,
    signals: dict[str, Any],
    score_result: dict[str, Any],
    alert_sent: bool,
    rate_limited: bool,
    notification_result: dict[str, Any] | None,
    recent_alert: Any | None,
) -> dict[str, Any]:
    is_critical = bool(score_result.get("critical"))
    level = "CRITICAL" if is_critical else ("WARNING" if score_result.get("weighted_score", 0) >= 0.5 else "STABLE")
    event = _select_event(score_result) if is_critical else "No emergency detected"
    action = "Seek immediate care" if is_critical else "Continue monitoring"

    alert_payload = {
        "level": level,
        "event": event,
        "confidence": score_result.get("confidence", 0.0),
        "action": action,
    }

    return {
        "success": True,
        "status": "ready",
        "source": "emergency_engine",
        "error": None,
        "data": {
            "user_id": str(user_id),
            "emergency": is_critical,
            "alert": alert_payload,
            "alert_sent": alert_sent,
            "rate_limited": rate_limited,
            "next_alert_after": _next_alert_after(recent_alert) if rate_limited else None,
            "notification": notification_result,
            "triggers": score_result.get("triggers", []),
            "evidence": score_result.get("evidence", []),
            "scores": score_result.get("scores", {}),
            "weighted_score": score_result.get("weighted_score", 0.0),
            "signals": signals,
        },
        "last_updated": _utc_now().isoformat(),
    }


def detect_emergency(
    user_id: Any,
    *,
    db: Session | None = None,
    signal_overrides: dict[str, Any] | None = None,
    trigger_alerts: bool = True,
) -> dict[str, Any]:
    """
    Detect the current emergency state for a user.

    The detector is synchronous by design so background workers can call it
    directly; HTTP routes should use detect_emergency_async() to avoid blocking
    the event loop.
    """
    managed_session = db is None
    session = db or SessionLocal()
    user_uuid = _coerce_user_uuid(user_id)

    try:
        if user_uuid is None:
            return {
                "success": False,
                "status": "failed",
                "source": "emergency_engine",
                "error": "Invalid user id",
                "data": None,
                "last_updated": _utc_now().isoformat(),
            }

        user = _load_user(session, user_uuid)
        if user is None:
            logger.info("[Emergency] Skipping detection for missing user=%s", user_id)
            return {
                "success": False,
                "status": "not_found",
                "source": "emergency_engine",
                "error": "User not found",
                "data": None,
                "last_updated": _utc_now().isoformat(),
            }

        signals = _apply_overrides(_collect_signals(session, user_uuid), signal_overrides)
        score_result = _score_signals(signals)
        alert_sent = False
        rate_limited = False
        recent_alert = None
        notification_result = None

        logger.info(
            "[Emergency] Detection user=%s critical=%s confidence=%s triggers=%s missing=%s",
            user_uuid,
            score_result.get("critical"),
            score_result.get("confidence"),
            score_result.get("triggers"),
            signals.get("missing"),
        )

        if score_result.get("critical") and trigger_alerts:
            recent_alert = _recent_critical_alert(session, user_uuid)
            if recent_alert is not None:
                rate_limited = True
                logger.info("[Emergency] Alert rate-limited user=%s recent_alert=%s", user_uuid, getattr(recent_alert, "id", None))
            else:
                alert_payload = {
                    "level": "CRITICAL",
                    "event": _select_event(score_result),
                    "confidence": score_result.get("confidence", 0.91),
                    "action": "Seek immediate care",
                }
                try:
                    notification_result = notification_service.send_alert(
                        str(user_uuid),
                        alert_payload,
                        channels=("push", "email", "dashboard"),
                        metadata={
                            "signals": signals,
                            "triggers": score_result.get("triggers", []),
                            "evidence": score_result.get("evidence", []),
                            "weighted_score": score_result.get("weighted_score"),
                            "rate_limit_minutes": RATE_LIMIT_MINUTES,
                        },
                    )
                    alert_sent = bool(notification_result and notification_result.get("success"))
                    logger.info("[Emergency] Alert triggered user=%s sent=%s event=%s", user_uuid, alert_sent, alert_payload["event"])
                except Exception as exc:
                    logger.exception("[Emergency] Alert trigger failed user=%s: %s", user_uuid, exc)
                    notification_result = {"success": False, "error": str(exc)}

        return _build_state(
            user_id=user_uuid,
            signals=signals,
            score_result=score_result,
            alert_sent=alert_sent,
            rate_limited=rate_limited,
            notification_result=notification_result,
            recent_alert=recent_alert,
        )
    except Exception as exc:
        logger.exception("[Emergency] Detection failed user=%s: %s", user_id, exc)
        return {
            "success": False,
            "status": "fallback",
            "source": "emergency_engine",
            "error": str(exc),
            "data": None,
            "last_updated": _utc_now().isoformat(),
        }
    finally:
        if managed_session:
            session.close()


async def detect_emergency_async(
    user_id: Any,
    *,
    signal_overrides: dict[str, Any] | None = None,
    trigger_alerts: bool = True,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        detect_emergency,
        user_id,
        signal_overrides=signal_overrides,
        trigger_alerts=trigger_alerts,
    )
