from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from core.serialization import make_json_safe
from database.session import SessionLocal
from models import ClinicalHistory, FeatureSnapshotRecord, LabResult, RiskScore, ShapValueRecord, UserVital


logger = logging.getLogger(__name__)
HIGH_RISK_THRESHOLD = 0.6

PRIORITY_RANK = {"low": 1, "medium": 2, "high": 3}
TIMELINE_RANK = {"ASAP": 1, "7 days": 2, "1 month": 3}

DIABETES_KEYWORDS = ("diabetes", "glucose", "hba1c", "insulin", "bmi", "activity", "metabolic")
CARDIO_KEYWORDS = (
    "cardio",
    "cardiovascular",
    "cad",
    "heart",
    "blood_pressure",
    "pressure",
    "cholesterol",
    "ldl",
    "lipid",
    "hrv",
    "resting",
    "palpitation",
)
RESPIRATORY_KEYWORDS = (
    "respiratory",
    "lung",
    "breathing",
    "breathlessness",
    "shortness",
    "oxygen",
    "spo2",
    "asthma",
    "copd",
)
SLEEP_KEYWORDS = ("sleep", "insomnia", "snoring", "apnea", "fatigue", "daytime")

DIABETES_SYMPTOMS = ("thirst", "urination", "fatigue", "blurred vision", "weight loss", "sugar")
CARDIO_SYMPTOMS = ("chest pain", "palpitation", "shortness of breath", "dizziness", "syncope", "breathlessness")
RESPIRATORY_SYMPTOMS = (
    "shortness of breath",
    "breathlessness",
    "wheezing",
    "cough",
    "chest tightness",
    "low oxygen",
)
SLEEP_SYMPTOMS = ("insomnia", "snoring", "apnea", "daytime sleepiness", "poor sleep", "fatigue")

CONDITION_ALIASES = {
    "cardio": "cardiovascular",
    "cardiovascular": "cardiovascular",
    "cad": "cardiovascular",
    "coronary": "cardiovascular",
    "heart": "cardiovascular",
    "hypertension": "cardiovascular",
    "blood pressure": "cardiovascular",
    "bp": "cardiovascular",
    "diabetes": "diabetes",
    "diabetes mellitus": "diabetes",
    "glucose": "diabetes",
    "hba1c": "diabetes",
    "metabolic": "diabetes",
    "respiratory": "respiratory",
    "respiratory strain": "respiratory",
    "lung": "respiratory",
    "breathing": "respiratory",
    "pulmonary": "respiratory",
    "sleep": "sleep",
}

PREDICTED_CONDITIONS = ("cardiovascular", "diabetes", "respiratory")


@dataclass
class RecommendationSignals:
    risk_score: float | None = None
    disease_probabilities: dict[str, float] = field(default_factory=dict)
    drivers: list[dict[str, Any]] = field(default_factory=list)
    vitals: dict[str, Any] = field(default_factory=dict)
    labs: list[dict[str, Any]] = field(default_factory=list)
    symptoms: dict[str, Any] = field(default_factory=dict)
    feature_snapshot: dict[str, Any] = field(default_factory=dict)
    has_ml: bool = False
    has_vitals: bool = False
    has_labs: bool = False
    has_symptoms: bool = False

    @property
    def has_any_data(self) -> bool:
        return self.has_ml or self.has_vitals or self.has_labs or self.has_symptoms


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_probability(value: Any) -> float | None:
    parsed = _safe_float(value)
    if parsed is None:
        return None
    if parsed > 1.0:
        parsed = parsed / 100.0
    return max(0.0, min(1.0, parsed))


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


def _lower_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return " ".join(_lower_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_lower_text(item) for item in value.values())
    return str(value).replace("_", " ").strip().lower()


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = _lower_text(text)
    return any(keyword.replace("_", " ") in normalized for keyword in keywords)


def _risk_value(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key in payload:
            value = _normalize_probability(payload.get(key))
            if value is not None:
                return value
    return None


def _risk_from_cards(cards: Any, *keys: str) -> float | None:
    if not isinstance(cards, list):
        return None

    aliases = {key.lower() for key in keys}
    values: list[float] = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        card_key = _lower_text(card.get("key") or card.get("label"))
        if any(alias in card_key for alias in aliases):
            value = _normalize_probability(card.get("score"))
            if value is not None:
                values.append(value)
    return max(values) if values else None


def _condition_key(value: Any) -> str | None:
    text = _lower_text(value)
    if not text:
        return None
    normalized = text.removesuffix(" risk").removesuffix(" score")
    normalized = normalized.removesuffix("_risk").removesuffix("_score")
    for alias, condition in CONDITION_ALIASES.items():
        if alias in normalized:
            return condition
    return None


def _fallback_condition_probabilities(risk_score: RiskScore | None, feature_payload: dict[str, Any]) -> dict[str, float]:
    if risk_score is None:
        return {}

    overall = _normalize_probability(risk_score.overall_score) or 0.0
    systolic_bp = _safe_float(feature_payload.get("systolic_bp"), 0.0) or 0.0
    diastolic_bp = _safe_float(feature_payload.get("diastolic_bp"), 0.0) or 0.0
    bmi = _safe_float(feature_payload.get("bmi"), 0.0) or 0.0
    glucose = _safe_float(feature_payload.get("glucose"), 0.0) or 0.0
    steps = _safe_float(feature_payload.get("activity_level") or feature_payload.get("steps"), 0.0) or 0.0
    sleep = _safe_float(feature_payload.get("sleep_duration") or feature_payload.get("sleep"), 0.0) or 0.0
    heart_rate = _safe_float(
        feature_payload.get("avg_rhr")
        or feature_payload.get("hr_mean_7d")
        or feature_payload.get("heart_rate"),
        0.0,
    ) or 0.0

    cardiovascular = overall
    diabetes = overall
    respiratory = overall * 0.75

    if systolic_bp >= 130 or diastolic_bp >= 80:
        cardiovascular += 0.08
    if steps < 5000:
        cardiovascular += 0.05
        diabetes += 0.06
        respiratory += 0.04
    if sleep < 6.5:
        cardiovascular += 0.04
        diabetes += 0.04
        respiratory += 0.08
    if bmi >= 30:
        cardiovascular += 0.06
        diabetes += 0.10
    if glucose >= 100:
        diabetes += 0.10
    if heart_rate >= 90:
        cardiovascular += 0.05
        respiratory += 0.05

    return {
        "cardiovascular": round(max(0.0, min(1.0, cardiovascular)), 4),
        "diabetes": round(max(0.0, min(1.0, diabetes)), 4),
        "respiratory": round(max(0.0, min(1.0, respiratory)), 4),
    }


def _extract_disease_probabilities(
    risk_score: RiskScore | None,
    feature_payload: dict[str, Any] | None = None,
) -> dict[str, float]:
    if risk_score is None:
        return {}

    payload = risk_score.risk_payload if isinstance(risk_score.risk_payload, dict) else {}
    risks = payload.get("risks") if isinstance(payload.get("risks"), dict) else {}
    combined = {**payload, **risks}
    cards = payload.get("cards")
    probabilities: dict[str, float] = {}

    for key, raw_value in combined.items():
        condition = _condition_key(key)
        if condition is None:
            continue
        value = _normalize_probability(raw_value)
        if value is not None:
            probabilities[condition] = max(probabilities.get(condition, 0.0), value)

    diabetes = (
        _risk_value(combined, "diabetes", "diabetes_risk")
        or _risk_from_cards(cards, "diabetes")
    )
    cardio_values = [
        _risk_value(combined, "cardio", "cardio_risk", "cardiovascular", "cardiovascular_risk"),
        _risk_value(combined, "cad", "cad_risk", "hypertension", "hypertension_risk"),
        _risk_from_cards(cards, "cardio", "cardiovascular", "cad", "hypertension"),
    ]
    sleep = (
        _risk_value(combined, "sleep", "sleep_risk")
        or _risk_from_cards(cards, "sleep")
    )
    respiratory = (
        _risk_value(combined, "respiratory", "respiratory_risk", "respiratory_score")
        or _risk_from_cards(cards, "respiratory", "lung", "pulmonary")
    )

    if diabetes is not None:
        probabilities["diabetes"] = max(probabilities.get("diabetes", 0.0), diabetes)

    cardio_candidates = [value for value in cardio_values if value is not None]
    if cardio_candidates:
        probabilities["cardiovascular"] = max(probabilities.get("cardiovascular", 0.0), max(cardio_candidates))

    if respiratory is not None:
        probabilities["respiratory"] = max(probabilities.get("respiratory", 0.0), respiratory)

    if sleep is not None:
        probabilities["sleep"] = max(probabilities.get("sleep", 0.0), sleep)

    if risk_score is not None and not all(condition in probabilities for condition in PREDICTED_CONDITIONS):
        for condition, probability in _fallback_condition_probabilities(risk_score, feature_payload or {}).items():
            probabilities.setdefault(condition, probability)

    return probabilities


def _extract_drivers(db: Session, risk_score: RiskScore | None) -> list[dict[str, Any]]:
    if risk_score is None:
        return []

    payload = risk_score.risk_payload if isinstance(risk_score.risk_payload, dict) else {}
    payload_drivers = payload.get("drivers")
    if isinstance(payload_drivers, list) and payload_drivers:
        return [driver for driver in payload_drivers if isinstance(driver, dict)]

    rows = (
        db.query(ShapValueRecord)
        .filter(ShapValueRecord.prediction_id == risk_score.id)
        .order_by(desc(ShapValueRecord.abs_shap_value), desc(ShapValueRecord.calculated_at))
        .limit(8)
        .all()
    )
    return [
        {
            "feature_name": row.feature_name,
            "shap_value": float(row.shap_value),
            "abs_shap_value": float(row.abs_shap_value),
            "direction": row.direction,
            "explanation": row.explanation,
        }
        for row in rows
    ]


def _driver_summary(drivers: list[dict[str, Any]], keywords: tuple[str, ...]) -> str | None:
    matches: list[str] = []
    for driver in drivers:
        label = str(driver.get("label") or driver.get("feature_name") or driver.get("key") or "").strip()
        detail = str(driver.get("detail") or driver.get("explanation") or "").strip()
        domains = _lower_text(driver.get("domains"))
        haystack = " ".join([label, detail, domains])
        if label and _contains_any(haystack, keywords):
            matches.append(label)
        if len(matches) >= 2:
            break

    if not matches:
        return None
    if len(matches) == 1:
        return f"Main related driver: {matches[0]}."
    return f"Main related drivers: {', '.join(matches)}."


def _latest_feature_payload(db: Session, user_id: UUID | str) -> dict[str, Any]:
    record = (
        db.query(FeatureSnapshotRecord)
        .filter(FeatureSnapshotRecord.user_id == user_id)
        .order_by(desc(FeatureSnapshotRecord.calculated_at))
        .first()
    )
    if record is None:
        return {}
    payload = record.feature_payload if isinstance(record.feature_payload, dict) else {}
    if payload:
        return dict(payload)
    return {
        "avg_rhr": _safe_float(record.hr_mean_7d),
        "steps_avg_7d": _safe_float(record.steps_avg_7d),
        "sleep_efficiency": _safe_float(record.sleep_efficiency),
        "bmi": _safe_float(record.bmi),
        "latest_observation_at": record.latest_observation_at.isoformat() if record.latest_observation_at else None,
    }


def _collect_vitals(db: Session, user_id: UUID | str, feature_payload: dict[str, Any]) -> dict[str, Any]:
    rows = (
        db.query(UserVital)
        .filter(UserVital.user_id == user_id)
        .order_by(desc(UserVital.timestamp))
        .limit(200)
        .all()
    )

    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        vital_type = _enum_value(row.vital_type)
        if vital_type in latest:
            continue
        latest[vital_type] = {
            "value": _safe_float(row.value),
            "unit": row.unit,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        }

    vitals = {
        "heart_rate": latest.get("heart_rate", {}).get("value"),
        "steps": latest.get("steps", {}).get("value"),
        "sleep_hours": _sleep_hours(latest.get("sleep", {}).get("value"), latest.get("sleep", {}).get("unit")),
        "systolic_bp": latest.get("blood_pressure_systolic", {}).get("value"),
        "diastolic_bp": latest.get("blood_pressure_diastolic", {}).get("value"),
        "fasting_glucose": latest.get("fasting_glucose", {}).get("value"),
        "source_rows": len(rows),
    }

    vitals["heart_rate"] = vitals["heart_rate"] or _safe_float(
        feature_payload.get("avg_rhr")
        or feature_payload.get("heart_rate")
        or feature_payload.get("hr_mean_7d")
    )
    vitals["steps"] = vitals["steps"] or _safe_float(feature_payload.get("steps") or feature_payload.get("steps_avg_7d"))
    vitals["sleep_hours"] = vitals["sleep_hours"] or _safe_float(
        feature_payload.get("sleep_duration")
        or feature_payload.get("sleep_hours")
        or feature_payload.get("sleep")
    )
    vitals["sleep_score"] = _safe_float(feature_payload.get("sleep_score"))
    vitals["sleep_efficiency"] = _safe_float(feature_payload.get("sleep_efficiency"))
    vitals["systolic_bp"] = vitals["systolic_bp"] or _safe_float(feature_payload.get("systolic_bp"))
    vitals["diastolic_bp"] = vitals["diastolic_bp"] or _safe_float(feature_payload.get("diastolic_bp"))
    vitals["fasting_glucose"] = vitals["fasting_glucose"] or _safe_float(
        feature_payload.get("fasting_glucose")
        or feature_payload.get("glucose")
        or feature_payload.get("blood_glucose")
        or feature_payload.get("blood_sugar")
    )

    return vitals


def _sleep_hours(value: Any, unit: Any = None) -> float | None:
    parsed = _safe_float(value)
    if parsed is None:
        return None
    normalized_unit = str(unit or "").lower()
    if normalized_unit.startswith("min") or parsed > 24:
        return round(parsed / 60.0, 2)
    return parsed


def _classify_lab_status(lab: LabResult) -> str:
    status = str(lab.status or "").strip().lower()
    if status:
        return status

    reference_range = str(lab.reference_range or "").strip()
    if not reference_range:
        return "unknown"

    import re

    range_match = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)$", reference_range)
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        if lab.value < low:
            return "low"
        if lab.value > high:
            return "high"
        return "normal"

    less_than_match = re.match(r"^<\s*([0-9]+(?:\.[0-9]+)?)$", reference_range)
    if less_than_match:
        return "high" if lab.value > float(less_than_match.group(1)) else "normal"

    greater_than_match = re.match(r"^>\s*([0-9]+(?:\.[0-9]+)?)$", reference_range)
    if greater_than_match:
        return "low" if lab.value < float(greater_than_match.group(1)) else "normal"

    return "unknown"


def _collect_labs(db: Session, user_id: UUID | str) -> list[dict[str, Any]]:
    rows = (
        db.query(LabResult)
        .filter(LabResult.user_id == user_id)
        .order_by(desc(LabResult.timestamp))
        .limit(100)
        .all()
    )
    latest_by_name: dict[str, LabResult] = {}
    for row in rows:
        key = _lower_text(row.name)
        if key and key not in latest_by_name:
            latest_by_name[key] = row

    labs: list[dict[str, Any]] = []
    for row in latest_by_name.values():
        labs.append(
            {
                "name": row.name,
                "value": row.value,
                "unit": row.unit,
                "reference_range": row.reference_range,
                "category": row.category,
                "status": _classify_lab_status(row),
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            }
        )
    return labs


def _collect_symptoms(db: Session, user_id: UUID | str) -> dict[str, Any]:
    row = (
        db.query(ClinicalHistory)
        .filter(ClinicalHistory.user_id == user_id)
        .order_by(desc(ClinicalHistory.created_at))
        .first()
    )
    if row is None:
        return {}

    symptoms = row.associated_symptoms if isinstance(row.associated_symptoms, list) else []
    return {
        "chief_complaint": row.chief_complaint,
        "associated_symptoms": symptoms,
        "severity": row.severity,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _collect_signals(db: Session, user_id: UUID | str) -> RecommendationSignals:
    latest_risk = (
        db.query(RiskScore)
        .filter(RiskScore.user_id == user_id)
        .order_by(desc(RiskScore.calculated_at), desc(RiskScore.created_at))
        .first()
    )
    feature_payload = _latest_feature_payload(db, user_id)
    labs = _collect_labs(db, user_id)
    symptoms = _collect_symptoms(db, user_id)
    vitals = _collect_vitals(db, user_id, feature_payload)

    return RecommendationSignals(
        risk_score=_normalize_probability(latest_risk.overall_score if latest_risk else None),
        disease_probabilities=_extract_disease_probabilities(latest_risk, feature_payload),
        drivers=_extract_drivers(db, latest_risk),
        vitals=vitals,
        labs=labs,
        symptoms=symptoms,
        feature_snapshot=feature_payload,
        has_ml=latest_risk is not None,
        has_vitals=bool(vitals.get("source_rows") or feature_payload),
        has_labs=bool(labs),
        has_symptoms=bool(symptoms),
    )


def _recommendation(
    test_name: str,
    reason: str,
    priority: str,
    timeline: str,
    confidence: float,
) -> dict[str, Any]:
    return {
        "test_name": test_name,
        "reason": reason,
        "priority": priority,
        "timeline": timeline,
        "confidence": round(max(0.0, min(1.0, confidence)), 2),
    }


def _merge_reason(existing: str, incoming: str) -> str:
    if not existing:
        return incoming
    if not incoming or incoming in existing:
        return existing
    return f"{existing} {incoming}"


def _add_recommendation(
    recommendations: dict[str, dict[str, Any]],
    *,
    test_name: str,
    reason: str,
    priority: str,
    timeline: str,
    confidence: float,
) -> None:
    key = _lower_text(test_name)
    candidate = _recommendation(test_name, reason, priority, timeline, confidence)
    existing = recommendations.get(key)
    if existing is None:
        recommendations[key] = candidate
        return

    if PRIORITY_RANK[candidate["priority"]] > PRIORITY_RANK[existing["priority"]]:
        existing["priority"] = candidate["priority"]
    if TIMELINE_RANK[candidate["timeline"]] < TIMELINE_RANK[existing["timeline"]]:
        existing["timeline"] = candidate["timeline"]
    existing["confidence"] = round(max(existing["confidence"], candidate["confidence"]), 2)
    existing["reason"] = _merge_reason(existing["reason"], candidate["reason"])


def _risk_reason(condition: str, probability: float, driver_text: str | None) -> str:
    reason = f"{condition} probability is {probability:.0%} from the latest ML risk model."
    if driver_text:
        reason = f"{reason} {driver_text}"
    return reason


def _is_abnormal(status: str) -> bool:
    normalized = str(status or "").lower()
    return normalized not in {"", "normal", "unknown", "ready"}


def _abnormal_priority(status: str) -> str:
    normalized = str(status or "").lower()
    if normalized in {"critical", "high", "low", "abnormal"}:
        return "high"
    return "medium"


def _abnormal_timeline(priority: str) -> str:
    return "ASAP" if priority == "high" else "7 days"


def _lab_follow_up_test(lab_name: str, category: str | None = None) -> str:
    text = _lower_text(f"{lab_name} {category or ''}")
    if _contains_any(text, ("glucose", "sugar", "hba1c")):
        return "HbA1c" if "glucose" in text else "Fasting glucose"
    if _contains_any(text, ("cholesterol", "ldl", "hdl", "triglyceride", "lipid")):
        return "Lipid profile"
    if _contains_any(text, ("hemoglobin", "wbc", "rbc", "platelet", "cbc")):
        return "CBC with differential"
    if _contains_any(text, ("creatinine", "egfr", "urea", "bun", "kidney", "renal")):
        return "Kidney function panel"
    if _contains_any(text, ("alt", "ast", "bilirubin", "liver", "sgpt", "sgot")):
        return "Liver function test"
    if _contains_any(text, ("thyroid", "tsh", "t3", "t4")):
        return "Thyroid profile"
    return f"Repeat {lab_name}"


def _sleep_issue_detected(signals: RecommendationSignals) -> bool:
    sleep_risk = signals.disease_probabilities.get("sleep")
    vitals = signals.vitals
    symptoms_text = _lower_text(signals.symptoms)
    return any(
        [
            sleep_risk is not None and sleep_risk > HIGH_RISK_THRESHOLD,
            (vitals.get("sleep_hours") is not None and float(vitals["sleep_hours"]) < 6.0),
            (vitals.get("sleep_score") is not None and float(vitals["sleep_score"]) < 72.0),
            (vitals.get("sleep_efficiency") is not None and float(vitals["sleep_efficiency"]) < 75.0),
            _contains_any(symptoms_text, SLEEP_SYMPTOMS),
        ]
    )


def _build_recommendations(signals: RecommendationSignals) -> list[dict[str, Any]]:
    recommendations: dict[str, dict[str, Any]] = {}

    diabetes = signals.disease_probabilities.get("diabetes")
    if diabetes is not None and diabetes > HIGH_RISK_THRESHOLD:
        reason = _risk_reason("Diabetes", diabetes, _driver_summary(signals.drivers, DIABETES_KEYWORDS))
        for test_name in ("HbA1c", "Fasting glucose"):
            _add_recommendation(
                recommendations,
                test_name=test_name,
                reason=reason,
                priority="medium",
                timeline="7 days",
                confidence=max(0.65, diabetes * 0.9),
            )

    cardio = signals.disease_probabilities.get("cardiovascular")
    if cardio is not None and cardio > HIGH_RISK_THRESHOLD:
        reason = _risk_reason("Cardiovascular", cardio, _driver_summary(signals.drivers, CARDIO_KEYWORDS))
        for test_name in ("ECG", "Lipid profile", "Holter monitor"):
            _add_recommendation(
                recommendations,
                test_name=test_name,
                reason=reason,
                priority="medium",
                timeline="7 days",
                confidence=max(0.65, cardio * 0.9),
            )

    if _sleep_issue_detected(signals):
        sleep_risk = signals.disease_probabilities.get("sleep") or 0.0
        reason_parts = ["Sleep disruption signal detected from recent risk, wearable, or symptom data."]
        sleep_hours = signals.vitals.get("sleep_hours")
        if sleep_hours is not None:
            reason_parts.append(f"Recent sleep duration is {float(sleep_hours):.1f} hours.")
        driver_text = _driver_summary(signals.drivers, SLEEP_KEYWORDS)
        if driver_text:
            reason_parts.append(driver_text)
        _add_recommendation(
            recommendations,
            test_name="Sleep study",
            reason=" ".join(reason_parts),
            priority="medium",
            timeline="7 days",
            confidence=max(0.68, sleep_risk * 0.9),
        )

    symptoms_text = _lower_text(signals.symptoms)
    symptom_severity = _safe_float(signals.symptoms.get("severity"))
    if _contains_any(symptoms_text, CARDIO_SYMPTOMS):
        priority = "high" if symptom_severity is None or symptom_severity >= 6 else "medium"
        for test_name in ("ECG", "Holter monitor"):
            _add_recommendation(
                recommendations,
                test_name=test_name,
                reason="Recent symptom history includes cardiovascular warning symptoms.",
                priority=priority,
                timeline=_abnormal_timeline(priority),
                confidence=0.86 if priority == "high" else 0.74,
            )

    if _contains_any(symptoms_text, DIABETES_SYMPTOMS):
        for test_name in ("HbA1c", "Fasting glucose"):
            _add_recommendation(
                recommendations,
                test_name=test_name,
                reason="Recent symptom history includes glucose-regulation warning symptoms.",
                priority="medium",
                timeline="7 days",
                confidence=0.72,
            )

    heart_rate = _safe_float(signals.vitals.get("heart_rate"))
    if heart_rate is not None and heart_rate >= 110:
        priority = "high" if heart_rate >= 120 else "medium"
        _add_recommendation(
            recommendations,
            test_name="ECG",
            reason=f"Latest heart-rate signal is elevated at {heart_rate:.0f} bpm.",
            priority=priority,
            timeline=_abnormal_timeline(priority),
            confidence=0.84 if priority == "high" else 0.72,
        )
        _add_recommendation(
            recommendations,
            test_name="Holter monitor",
            reason=f"Latest heart-rate signal is elevated at {heart_rate:.0f} bpm.",
            priority=priority,
            timeline=_abnormal_timeline(priority),
            confidence=0.82 if priority == "high" else 0.7,
        )

    systolic = _safe_float(signals.vitals.get("systolic_bp"))
    diastolic = _safe_float(signals.vitals.get("diastolic_bp"))
    if (systolic is not None and systolic >= 140) or (diastolic is not None and diastolic >= 90):
        reading = "/".join(str(int(value)) for value in (systolic, diastolic) if value is not None)
        for test_name in ("ECG", "Lipid profile"):
            _add_recommendation(
                recommendations,
                test_name=test_name,
                reason=f"Recent blood-pressure signal is elevated ({reading}).",
                priority="high",
                timeline="ASAP",
                confidence=0.84,
            )

    for lab in signals.labs:
        status = str(lab.get("status") or "").lower()
        if not _is_abnormal(status):
            continue
        priority = _abnormal_priority(status)
        lab_name = str(lab.get("name") or "lab value").strip()
        follow_up = _lab_follow_up_test(lab_name, lab.get("category"))
        reason = f"Latest {lab_name} lab result is {status}."
        _add_recommendation(
            recommendations,
            test_name=follow_up,
            reason=reason,
            priority=priority,
            timeline=_abnormal_timeline(priority),
            confidence=0.92 if priority == "high" else 0.78,
        )

    if not recommendations:
        reason = (
            "Insufficient recent ML, lab, wearable, or symptom signals for a targeted test recommendation."
            if not signals.has_any_data
            else "Current ML, lab, wearable, and symptom signals do not require a targeted follow-up right now."
        )
        _add_recommendation(
            recommendations,
            test_name="Baseline preventive tests",
            reason=reason,
            priority="low",
            timeline="1 month",
            confidence=0.35 if not signals.has_any_data else 0.45,
        )

    ordered = sorted(
        recommendations.values(),
        key=lambda item: (
            -PRIORITY_RANK[item["priority"]],
            TIMELINE_RANK[item["timeline"]],
            -item["confidence"],
            item["test_name"],
        ),
    )
    return ordered


def generate_test_recommendations(user_id: UUID | str, db: Session | None = None) -> list[dict[str, Any]]:
    """
    Generate real-time clinical test recommendations for a user.

    The engine intentionally reads the latest persisted risk, SHAP, lab, vital,
    and symptom rows on each call so dashboard output changes immediately after
    sync, lab upload, ML refresh, or clinical-history update.
    """
    owns_session = db is None
    session = db or SessionLocal()
    try:
        signals = _collect_signals(session, user_id)
        return make_json_safe(_build_recommendations(signals))
    except Exception as exc:
        logger.exception("Failed to generate test recommendations for user=%s: %s", user_id, exc)
        return make_json_safe([
            _recommendation(
                "Baseline preventive tests",
                "Recommendation engine could not read enough current signals; start with routine preventive screening.",
                "low",
                "1 month",
                0.25,
            )
        ])
    finally:
        if owns_session:
            session.close()


def recommendations_last_updated() -> str:
    return datetime.now(timezone.utc).isoformat()
