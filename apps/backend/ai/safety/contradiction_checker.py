from __future__ import annotations

import logging
import re

from .safety_types import ContradictionReport, ConversationContext

logger = logging.getLogger("arogyaai.safety.contradiction")

_VITAL_RISK_THRESHOLDS = {
    "systolic_bp": {"high": 140, "critical": 180},
    "diastolic_bp": {"high": 90, "critical": 120},
    "heart_rate": {"high": 100, "critical": 120, "low": 50},
    "spo2": {"low": 94, "critical_low": 88},
    "glucose": {"high": 180, "critical": 250, "low": 70, "critical_low": 54},
    "bmi": {"high": 30, "critical": 40},
}

_REASSURANCE_PATTERNS = [
    re.compile(r"(?:looks?|seems?|appears?) (?:generally |mostly )?(?:fine|okay|normal|healthy|good)", re.IGNORECASE),
    re.compile(r"(?:no|nothing|not much|low) (?:significant|serious|major|immediate) (?:concern|risk|issue|problem)", re.IGNORECASE),
    re.compile(r"(?:cardiovascular|heart|cardiac).{0,30}(?:fine|okay|normal|healthy|low risk)", re.IGNORECASE),
    re.compile(r"blood pressure.{0,30}(?:fine|okay|normal|stable)", re.IGNORECASE),
    re.compile(r"blood sugar.{0,30}(?:fine|okay|normal|controlled)", re.IGNORECASE),
    re.compile(r"heart rate.{0,30}(?:fine|okay|normal|stable)", re.IGNORECASE),
]


def check_contradictions(ai_response: str, context: ConversationContext) -> ContradictionReport:
    try:
        contradictions: list[dict[str, object]] = []
        is_reassuring = _is_reassuring(ai_response)
        vital_risks = _assess_vital_risks(context.vitals)
        ml_risks = _assess_ml_risks(context.ml_predictions)

        if is_reassuring:
            for field, risk_level in vital_risks.items():
                if risk_level in {"high", "critical"}:
                    contradictions.append(
                        {
                            "field": field,
                            "ai_claim": "reassurance/downplay",
                            "actual_value": context.vitals.get(field),
                            "risk_level": risk_level,
                            "severity": "critical" if risk_level == "critical" else "major",
                        }
                    )
            for disease, risk_level in ml_risks.items():
                if risk_level in {"high", "critical"}:
                    contradictions.append(
                        {
                            "field": f"ml_{disease}_risk",
                            "ai_claim": "reassurance/downplay",
                            "actual_value": context.ml_predictions.get(disease),
                            "risk_level": risk_level,
                            "severity": "major" if risk_level == "high" else "critical",
                        }
                    )

        severity = _compute_severity(contradictions)
        if contradictions:
            logger.warning(
                "Contradiction detected",
                extra={"count": len(contradictions), "severity": severity, "user_id": context.user_id},
            )

        return ContradictionReport(
            detected=bool(contradictions),
            contradictions=contradictions,
            severity=severity,
        )
    except Exception as exc:
        logger.error("Contradiction checker failed: %s", exc, exc_info=True)
        return ContradictionReport(detected=False, contradictions=[], severity="none")


def _is_reassuring(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in _REASSURANCE_PATTERNS)


def _assess_vital_risks(vitals: dict[str, object]) -> dict[str, str]:
    risks: dict[str, str] = {}
    for field, thresholds in _VITAL_RISK_THRESHOLDS.items():
        value = vitals.get(field)
        if value is None:
            continue
        numeric = float(value)
        if "critical" in thresholds and numeric >= thresholds["critical"]:
            risks[field] = "critical"
        elif "high" in thresholds and numeric >= thresholds["high"]:
            risks[field] = "high"
        elif "critical_low" in thresholds and numeric <= thresholds["critical_low"]:
            risks[field] = "critical"
        elif "low" in thresholds and numeric <= thresholds["low"]:
            risks[field] = "high"
    return risks


def _assess_ml_risks(ml_predictions: dict[str, object]) -> dict[str, str]:
    risks: dict[str, str] = {}
    for disease, prediction in ml_predictions.items():
        probability = prediction.get("probability", prediction) if isinstance(prediction, dict) else prediction
        numeric = float(probability or 0.0)
        if numeric >= 0.75:
            risks[disease] = "critical"
        elif numeric >= 0.55:
            risks[disease] = "high"
    return risks


def _compute_severity(contradictions: list[dict[str, object]]) -> str:
    if not contradictions:
        return "none"
    severities = [str(item.get("severity") or "") for item in contradictions]
    if "critical" in severities:
        return "critical"
    if len(contradictions) >= 2 or "major" in severities:
        return "major"
    return "minor"
