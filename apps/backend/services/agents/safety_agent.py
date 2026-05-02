from __future__ import annotations

from typing import Any


RISK_LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}

RED_FLAG_TERMS = {
    "chest pain": "Chest pain can require urgent assessment when new, severe, exertional, or paired with breathlessness, sweating, dizziness, or fainting.",
    "chest pressure": "Chest pressure can require urgent assessment.",
    "pressure in chest": "Chest pressure can require urgent assessment.",
    "shortness of breath": "Shortness of breath can be urgent when severe, new, or present at rest.",
    "severe breathlessness": "Severe breathlessness can require urgent assessment.",
    "can't breathe": "Severe breathing difficulty can require urgent assessment.",
    "cannot breathe": "Severe breathing difficulty can require urgent assessment.",
    "fainting": "Fainting can indicate a potentially serious rhythm, circulation, neurologic, or metabolic issue.",
    "fainted": "Fainting can indicate a potentially serious rhythm, circulation, neurologic, or metabolic issue.",
    "passed out": "Passing out can indicate a potentially serious rhythm, circulation, neurologic, or metabolic issue.",
    "stroke": "Stroke-like symptoms need emergency evaluation.",
    "one sided weakness": "One-sided weakness can be a stroke warning symptom.",
    "slurred speech": "Slurred speech can be a stroke warning symptom.",
    "severe bleeding": "Severe bleeding needs emergency evaluation.",
}


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_probability(value: Any, default: float | None = None) -> float | None:
    numeric = _safe_float(value, default)
    if numeric is None:
        return None
    if abs(numeric) > 1:
        numeric /= 100.0
    return max(0.0, min(1.0, numeric))


def _normalize_risk_level(value: Any) -> str:
    candidate = _clean_text(value).upper()
    if candidate == "CRITICAL":
        return "HIGH"
    if candidate == "MODERATE":
        return "MEDIUM"
    if candidate in {"LOW", "MEDIUM", "HIGH"}:
        return candidate
    return "LOW"


def _max_risk(*levels: Any) -> str:
    normalized = [_normalize_risk_level(level) for level in levels]
    return max(normalized or ["LOW"], key=lambda level: RISK_LEVEL_ORDER.get(level, 0))


def _symptom_names(symptom_payload: dict[str, Any]) -> list[str]:
    if not isinstance(symptom_payload, dict):
        return []
    values = symptom_payload.get("symptom_names")
    if isinstance(values, list):
        return [_clean_text(item) for item in values if _clean_text(item)]
    return []


def _vital_value(vitals: dict[str, Any], key: str) -> float | None:
    row = vitals.get(key) if isinstance(vitals, dict) else None
    if isinstance(row, dict):
        return _safe_float(row.get("latest"))
    return _safe_float(row)


class SafetyGuardAgent:
    """Screens red flags and upgrades risk when immediate care language is needed."""

    name = "safety_guard_agent"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        query = _clean_text(context.get("query")).lower()
        symptom_payload = context.get("symptoms") if isinstance(context.get("symptoms"), dict) else {}
        symptoms = " ".join(_symptom_names(symptom_payload)).lower()
        combined_text = f"{query} {symptoms}"
        ml_data = context.get("ml_data") if isinstance(context.get("ml_data"), dict) else {}
        ml_interpretation = context.get("ml_interpretation") if isinstance(context.get("ml_interpretation"), dict) else {}
        reasoning = context.get("clinical_reasoning") if isinstance(context.get("clinical_reasoning"), dict) else {}
        vitals = context.get("vitals") if isinstance(context.get("vitals"), dict) else {}
        labs = context.get("labs") if isinstance(context.get("labs"), dict) else {}

        red_flags = [
            {"trigger": term, "reason": reason}
            for term, reason in RED_FLAG_TERMS.items()
            if term in combined_text
        ]
        red_flags.extend(symptom_payload.get("red_flags") or [])

        vital_alerts: list[str] = []
        heart_rate = _vital_value(vitals, "heart_rate")
        systolic = _vital_value(vitals, "blood_pressure_systolic")
        spo2 = _vital_value(vitals, "oxygen_saturation") or _vital_value(vitals, "spo2")
        temperature = _vital_value(vitals, "temperature")
        if heart_rate is not None and heart_rate >= 120:
            vital_alerts.append("Resting heart rate is very elevated.")
        if systolic is not None and systolic >= 180:
            vital_alerts.append("Systolic blood pressure is in a very high range.")
        if spo2 is not None and spo2 <= 92:
            vital_alerts.append("Oxygen saturation is low.")
        if temperature is not None and temperature >= 103:
            vital_alerts.append("Temperature is very high.")

        abnormal_labs = labs.get("abnormal") if isinstance(labs, dict) else []
        lab_alerts = []
        for lab in abnormal_labs or []:
            if isinstance(lab, dict) and _clean_text(lab.get("status")).lower() in {"critical", "panic"}:
                lab_alerts.append(f"Critical lab result reported for {lab.get('name') or 'a recent lab'}.")

        risk_score = _normalize_probability(ml_data.get("overall_risk"), _normalize_probability(ml_interpretation.get("risk_score")))
        ml_risk = "HIGH" if risk_score is not None and risk_score > 0.75 else _normalize_risk_level(ml_interpretation.get("risk_level"))
        risk_level = _max_risk(reasoning.get("risk_level"), ml_risk)
        if red_flags or vital_alerts or lab_alerts:
            risk_level = "HIGH"

        requires_immediate_care = bool(red_flags) or any(
            "oxygen" in alert.lower() or "very high" in alert.lower()
            for alert in vital_alerts
        )
        override = requires_immediate_care or risk_level == "HIGH"

        if requires_immediate_care:
            safety_notes = [
                "Seek immediate medical care now, especially if symptoms are severe, worsening, or paired with fainting, shortness of breath, new weakness, or persistent chest pressure."
            ]
        elif risk_level == "HIGH":
            safety_notes = [
                "Please arrange prompt clinical evaluation, especially if symptoms are new, persistent, worsening, or different from your usual pattern."
            ]
        else:
            safety_notes = [
                "This assistant suggests possibilities and next steps, but it does not provide a diagnosis."
            ]

        recommendations = []
        if requires_immediate_care:
            recommendations.append("Do not wait for app-based monitoring if the red-flag symptoms are happening now.")
        elif risk_level == "HIGH":
            recommendations.append("Arrange prompt clinical evaluation rather than relying on self-monitoring alone.")

        return {
            "agent": self.name,
            "risk_level": risk_level,
            "override": override,
            "requires_immediate_care": requires_immediate_care,
            "red_flags": red_flags,
            "vital_alerts": vital_alerts,
            "lab_alerts": lab_alerts,
            "safety_notes": safety_notes,
            "recommendations": recommendations,
        }


def evaluate_safety(context: dict[str, Any]) -> dict[str, Any]:
    return SafetyGuardAgent().run(context)
