from __future__ import annotations

from typing import Any

from services.agents.safety_agent import evaluate_safety


RISK_LABELS = {
    "LOW": "Low",
    "MEDIUM": "Moderate",
    "HIGH": "Elevated",
}

URGENCY_BY_RISK = {
    "LOW": "Routine monitoring",
    "MEDIUM": "Clinical follow-up soon",
    "HIGH": "Prompt medical attention",
}


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if item]
    return []


def assess_symptom_risk(context: dict[str, Any]) -> dict[str, Any]:
    safety = evaluate_safety(context)
    risk_level = _clean_text(safety.get("risk_level")).upper() or "LOW"
    red_flags = _coerce_list(safety.get("red_flags"))
    vital_alerts = _coerce_list(safety.get("vital_alerts"))
    lab_alerts = _coerce_list(safety.get("lab_alerts"))

    risk_indicators: list[str] = []
    for item in red_flags:
        if isinstance(item, dict):
            reason = _clean_text(item.get("reason"))
            if reason:
                risk_indicators.append(reason)
        else:
            text = _clean_text(item)
            if text:
                risk_indicators.append(text)
    for item in vital_alerts + lab_alerts:
        text = _clean_text(item)
        if text and text not in risk_indicators:
            risk_indicators.append(text)

    return {
        **safety,
        "risk_level_display": RISK_LABELS.get(risk_level, "Low"),
        "urgency_level": URGENCY_BY_RISK.get(risk_level, "Routine monitoring"),
        "risk_indicators": risk_indicators[:5],
        "warning_banner": bool(safety.get("requires_immediate_care")) or risk_level == "HIGH",
    }
