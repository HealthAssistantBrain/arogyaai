from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.session import SessionLocal
from models import ClinicalHistory, RiskScore, UserProfile, UserVital, UserVitalTypeEnum, WearableMetric


logger = logging.getLogger(__name__)

TREND_MIN_POINTS = 3
TREND_LIMIT = 10
LATEST_ROW_LIMIT = 250


@dataclass(frozen=True)
class VitalReading:
    metric: str
    value: float | None
    unit: str | None = None
    timestamp: Any = None


VITAL_TYPES = {
    "steps": UserVitalTypeEnum.STEPS,
    "heart_rate": UserVitalTypeEnum.HEART_RATE,
    "sleep": UserVitalTypeEnum.SLEEP,
    "spo2": UserVitalTypeEnum.SPO2,
    "glucose": UserVitalTypeEnum.GLUCOSE,
    "temperature": UserVitalTypeEnum.BODY_TEMPERATURE,
    "systolic_bp": UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC,
    "diastolic_bp": UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC,
}

WEARABLE_ALIASES = {
    "steps": ("steps", "step_count", "stepCount"),
    "heart_rate": ("heart_rate", "heartRate", "hr", "latest_heart_rate"),
    "sleep": ("sleep", "sleep_hours", "sleepHours", "sleep_duration", "duration_hours"),
    "spo2": ("spo2", "spO2", "oxygen_saturation_spo2"),
    "glucose": ("glucose", "blood_glucose", "bloodGlucose", "fasting_glucose"),
    "temperature": ("temperature", "body_temperature", "bodyTemperature", "body_temp"),
    "systolic_bp": ("blood_pressure_systolic", "systolic_bp", "sbp"),
    "diastolic_bp": ("blood_pressure_diastolic", "diastolic_bp", "dbp"),
}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    numeric = _safe_float(value)
    return int(round(numeric)) if numeric is not None else None


def _normalize_probability(value: Any) -> float | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    if numeric > 1.0:
        numeric /= 100.0
    return round(max(0.0, min(1.0, numeric)), 4)


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


def _normalize_unit(unit: Any) -> str:
    return str(unit or "").strip().lower()


def _normalize_glucose(value: Any, unit: Any = None) -> float | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    normalized_unit = _normalize_unit(unit)
    if normalized_unit in {"mmol/l", "mmol"}:
        numeric *= 18.0182
    return round(numeric, 1)


def _normalize_temperature(value: Any, unit: Any = None) -> float | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    normalized_unit = _normalize_unit(unit)
    if normalized_unit in {"f", "fahrenheit", "degf", "°f"}:
        numeric = (numeric - 32.0) * 5.0 / 9.0
    return round(numeric, 1)


def _normalize_sleep(value: Any, unit: Any = None) -> float | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    normalized_unit = _normalize_unit(unit)
    if normalized_unit.startswith("min") or numeric > 24:
        numeric /= 60.0
    return round(numeric, 2)


def _normalize_vital_value(metric: str, value: Any, unit: Any = None) -> float | int | None:
    if metric == "steps":
        return _safe_int(value)
    if metric == "heart_rate":
        return _safe_int(value)
    if metric == "sleep":
        return _normalize_sleep(value, unit)
    if metric == "spo2":
        numeric = _safe_float(value)
        return round(numeric, 1) if numeric is not None else None
    if metric == "glucose":
        return _normalize_glucose(value, unit)
    if metric == "temperature":
        return _normalize_temperature(value, unit)
    return _safe_float(value)


def _profile_payload(profile: UserProfile | None) -> dict[str, Any]:
    if profile is None:
        logger.info("Context builder missing user_profile row")
        return {
            "age": None,
            "gender": None,
            "weight": None,
            "height": None,
        }

    return {
        "age": _safe_int(profile.age),
        "gender": str(profile.gender).strip() if profile.gender else None,
        "weight": _safe_float(profile.weight_kg),
        "height": _safe_float(profile.height_cm),
    }


def _get_profile(db: Session, user_id: UUID | str) -> UserProfile | None:
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).one_or_none()


def _fetch_vital_rows(db: Session, user_id: UUID | str, *, limit: int = LATEST_ROW_LIMIT) -> list[UserVital]:
    return (
        db.query(UserVital)
        .filter(UserVital.user_id == user_id)
        .order_by(desc(UserVital.timestamp))
        .limit(limit)
        .all()
    )


def _fetch_wearable_rows(
    db: Session,
    user_id: UUID | str,
    metric: str,
    *,
    limit: int = TREND_LIMIT,
) -> list[WearableMetric]:
    aliases = WEARABLE_ALIASES.get(metric, (metric,))
    return (
        db.query(WearableMetric)
        .filter(WearableMetric.user_id == user_id, WearableMetric.metric_type.in_(aliases))
        .order_by(desc(WearableMetric.timestamp))
        .limit(limit)
        .all()
    )


def _latest_from_wearables(db: Session, user_id: UUID | str, metric: str) -> VitalReading:
    row = (
        db.query(WearableMetric)
        .filter(WearableMetric.user_id == user_id, WearableMetric.metric_type.in_(WEARABLE_ALIASES.get(metric, (metric,))))
        .order_by(desc(WearableMetric.timestamp))
        .first()
    )
    if row is None:
        return VitalReading(metric=metric, value=None)
    return VitalReading(metric=metric, value=_safe_float(row.value), unit=row.unit, timestamp=row.timestamp)


def _latest_readings_by_metric(rows: Iterable[UserVital]) -> dict[str, VitalReading]:
    latest: dict[str, VitalReading] = {}
    type_to_metric = {vital_type.value: metric for metric, vital_type in VITAL_TYPES.items()}
    for row in rows:
        metric = type_to_metric.get(_enum_value(row.vital_type))
        if not metric or metric in latest:
            continue
        latest[metric] = VitalReading(metric=metric, value=_safe_float(row.value), unit=row.unit, timestamp=row.timestamp)
    return latest


def _blood_pressure_value(systolic: Any, diastolic: Any) -> str | None:
    systolic_value = _safe_int(systolic)
    diastolic_value = _safe_int(diastolic)
    if systolic_value is None or diastolic_value is None:
        return None
    if systolic_value == diastolic_value:
        logger.warning(
            "INVALID_BP_BLOCKED | stage=context_builder | systolic=%s | diastolic=%s",
            systolic_value,
            diastolic_value,
        )
        return None
    return f"{systolic_value}/{diastolic_value}"


def compute_trend(values: list[Any]) -> str:
    """
    Return increasing, decreasing, stable, or unknown from the most recent 5-10 values.

    The function expects chronological order when available, but still works for
    any numeric sequence because it compares the first half to the second half.
    """
    numeric_values = [_safe_float(value) for value in values]
    numeric_values = [value for value in numeric_values if value is not None]
    if len(numeric_values) < TREND_MIN_POINTS:
        return "unknown"

    recent = numeric_values[-TREND_LIMIT:]
    midpoint = max(1, len(recent) // 2)
    first_half = recent[:midpoint]
    second_half = recent[midpoint:]
    if not first_half or not second_half:
        return "unknown"

    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    delta = second_avg - first_avg
    baseline = max(abs(first_avg), 1.0)
    relative_change = abs(delta) / baseline

    if relative_change < 0.05:
        return "stable"
    return "increasing" if delta > 0 else "decreasing"


def _series_from_vitals(rows: Iterable[UserVital], metric: str) -> list[float]:
    vital_type = VITAL_TYPES.get(metric)
    if vital_type is None:
        return []
    values = [
        _safe_float(row.value)
        for row in rows
        if row.vital_type == vital_type and _safe_float(row.value) is not None
    ]
    return list(reversed(values[:TREND_LIMIT]))


def _series_from_wearables(db: Session, user_id: UUID | str, metric: str) -> list[float]:
    rows = _fetch_wearable_rows(db, user_id, metric, limit=TREND_LIMIT)
    values = [_safe_float(row.value) for row in rows]
    return list(reversed([value for value in values if value is not None]))


def _metric_series(db: Session, user_id: UUID | str, vital_rows: list[UserVital], metric: str) -> list[float]:
    series = _series_from_vitals(vital_rows, metric)
    if len(series) >= TREND_MIN_POINTS:
        return series
    return _series_from_wearables(db, user_id, metric)


def _bp_series(db: Session, user_id: UUID | str, vital_rows: list[UserVital]) -> list[float]:
    systolic_series = _series_from_vitals(vital_rows, "systolic_bp")
    if len(systolic_series) >= TREND_MIN_POINTS:
        return systolic_series
    wearable_series = _series_from_wearables(db, user_id, "systolic_bp")
    if len(wearable_series) >= TREND_MIN_POINTS:
        return wearable_series
    return []


def get_latest_vitals(user_id: UUID | str, db: Session | None = None) -> dict[str, Any]:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        rows = _fetch_vital_rows(session, user_id)
        latest = _latest_readings_by_metric(rows)

        def latest_value(metric: str) -> VitalReading:
            reading = latest.get(metric)
            if reading is not None and reading.value is not None:
                return reading
            wearable_reading = _latest_from_wearables(session, user_id, metric)
            if wearable_reading.value is None:
                logger.info("Context builder missing latest vital metric=%s user=%s", metric, user_id)
            return wearable_reading

        steps = latest_value("steps")
        heart_rate = latest_value("heart_rate")
        sleep = latest_value("sleep")
        spo2 = latest_value("spo2")
        glucose = latest_value("glucose")
        temperature = latest_value("temperature")
        systolic = latest_value("systolic_bp")
        diastolic = latest_value("diastolic_bp")

        return {
            "steps": _normalize_vital_value("steps", steps.value, steps.unit),
            "heart_rate": _normalize_vital_value("heart_rate", heart_rate.value, heart_rate.unit),
            "sleep": _normalize_vital_value("sleep", sleep.value, sleep.unit),
            "spo2": _normalize_vital_value("spo2", spo2.value, spo2.unit),
            "glucose": _normalize_vital_value("glucose", glucose.value, glucose.unit),
            "blood_pressure": _blood_pressure_value(systolic.value, diastolic.value),
            "temperature": _normalize_vital_value("temperature", temperature.value, temperature.unit),
        }
    except Exception as exc:
        logger.exception("Context builder failed to fetch latest vitals user=%s: %s", user_id, exc)
        return _empty_vitals()
    finally:
        if owns_session:
            session.close()


def _empty_vitals() -> dict[str, Any]:
    return {
        "steps": None,
        "heart_rate": None,
        "sleep": None,
        "spo2": None,
        "glucose": None,
        "blood_pressure": None,
        "temperature": None,
    }


def _build_trends(db: Session, user_id: UUID | str, vital_rows: list[UserVital]) -> dict[str, str]:
    return {
        "steps_trend": compute_trend(_metric_series(db, user_id, vital_rows, "steps")),
        "heart_rate_trend": compute_trend(_metric_series(db, user_id, vital_rows, "heart_rate")),
        "bp_trend": compute_trend(_bp_series(db, user_id, vital_rows)),
        "glucose_trend": compute_trend(_metric_series(db, user_id, vital_rows, "glucose")),
    }


def _empty_trends() -> dict[str, str]:
    return {
        "steps_trend": "unknown",
        "heart_rate_trend": "unknown",
        "bp_trend": "unknown",
        "glucose_trend": "unknown",
    }


def _prediction_items_from_payload(risk_score: RiskScore) -> list[dict[str, Any]]:
    payload = risk_score.risk_payload if isinstance(risk_score.risk_payload, dict) else {}
    risks = payload.get("risks") if isinstance(payload.get("risks"), dict) else {}
    confidence = _normalize_probability(risk_score.confidence_score)
    if confidence is None:
        confidence = _normalize_probability(risk_score.overall_score) or 0.0
    predictions: list[dict[str, Any]] = []

    for condition, risk in risks.items():
        normalized_risk = _normalize_probability(risk)
        if normalized_risk is None:
            continue
        predictions.append(
            {
                "condition": str(condition).replace("_risk", "").replace("_score", ""),
                "risk": normalized_risk,
                "confidence": confidence,
            }
        )

    if predictions:
        return predictions

    overall_risk = _normalize_probability(risk_score.overall_score)
    if overall_risk is None:
        return []
    return [
        {
            "condition": "overall",
            "risk": overall_risk,
            "confidence": confidence,
        }
    ]


def fetch_predictions(user_id: UUID | str, db: Session | None = None) -> list[dict[str, Any]]:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        latest = (
            session.query(RiskScore)
            .filter(RiskScore.user_id == user_id)
            .order_by(desc(RiskScore.calculated_at), desc(RiskScore.created_at))
            .first()
        )
        if latest is None:
            logger.info("Context builder missing risk predictions user=%s", user_id)
            return []
        return _prediction_items_from_payload(latest)
    except Exception as exc:
        logger.exception("Context builder failed to fetch predictions user=%s: %s", user_id, exc)
        return []
    finally:
        if owns_session:
            session.close()


def _fetch_symptoms(db: Session, user_id: UUID | str) -> list[str]:
    row = (
        db.query(ClinicalHistory)
        .filter(ClinicalHistory.user_id == user_id)
        .order_by(desc(ClinicalHistory.created_at))
        .first()
    )
    if row is None:
        logger.info("Context builder missing symptoms user=%s", user_id)
        return []

    symptoms: list[str] = []
    if row.chief_complaint:
        symptoms.append(str(row.chief_complaint).strip())
    if isinstance(row.associated_symptoms, list):
        symptoms.extend(str(item).strip() for item in row.associated_symptoms if str(item).strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for symptom in symptoms:
        key = symptom.lower()
        if not symptom or key in seen:
            continue
        seen.add(key)
        deduped.append(symptom)
    return deduped


def build_context(user_id: UUID | str, db: Session | None = None) -> dict[str, Any]:
    """
    Build the exact LLM context object used by recommendation generation.

    All DB reads are bounded and fault tolerant. Missing tables/rows return
    nulls or empty lists rather than raising into caller code.
    """
    owns_session = db is None
    session = db or SessionLocal()
    try:
        vital_rows = _fetch_vital_rows(session, user_id)
        return {
            "user_profile": _profile_payload(_get_profile(session, user_id)),
            "risk_predictions": fetch_predictions(user_id, db=session),
            "vitals": get_latest_vitals(user_id, db=session),
            "trends": _build_trends(session, user_id, vital_rows),
            "symptoms": _fetch_symptoms(session, user_id),
        }
    except Exception as exc:
        logger.exception("Context builder failed user=%s: %s", user_id, exc)
        return {
            "user_profile": _profile_payload(None),
            "risk_predictions": [],
            "vitals": _empty_vitals(),
            "trends": _empty_trends(),
            "symptoms": [],
        }
    finally:
        if owns_session:
            session.close()
