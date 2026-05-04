from __future__ import annotations

from typing import Any


RISK_LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}


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


def _feature_label(feature_name: Any) -> str:
    text = _clean_text(feature_name)
    parts = [part for part in text.replace("-", "_").split("_") if part]
    return " ".join(part.upper() if len(part) <= 3 else part.capitalize() for part in parts) or "Health driver"


def _normalize_risk_level(value: Any, *, score: float | None = None) -> str:
    candidate = _clean_text(value).upper()
    if candidate == "CRITICAL":
        label_level = "HIGH"
    elif candidate == "MODERATE":
        label_level = "MEDIUM"
    elif candidate in {"LOW", "MEDIUM", "HIGH"}:
        label_level = candidate
    else:
        label_level = "LOW"

    score_level = "LOW"
    if score is not None:
        if score > 0.75:
            score_level = "HIGH"
        elif score >= 0.4:
            score_level = "MEDIUM"

    return max((label_level, score_level), key=lambda level: RISK_LEVEL_ORDER.get(level, 0))


def _coerce_condition_risks(ml_data: dict[str, Any]) -> dict[str, float]:
    risks = ml_data.get("condition_risks") if isinstance(ml_data.get("condition_risks"), dict) else {}
    if not risks:
        risks = {
            "cardiovascular": ml_data.get("cardio_risk"),
            "diabetes": ml_data.get("diabetes_risk"),
            "respiratory": ml_data.get("respiratory_risk"),
            "sleep": ml_data.get("sleep_risk"),
        }
    normalized: dict[str, float] = {}
    for key, value in risks.items():
        numeric = _normalize_probability(value)
        if numeric is not None:
            normalized[str(key)] = round(numeric, 4)
    return normalized


def _driver_impact(driver: dict[str, Any]) -> float:
    for key in ("abs_shap_value", "impact", "shap_value"):
        value = _safe_float(driver.get(key))
        if value is not None:
            return abs(value)
    return 0.0


def _normalize_driver(driver: dict[str, Any]) -> dict[str, Any]:
    label = _clean_text(driver.get("label") or driver.get("display_name") or _feature_label(driver.get("feature_name")))
    direction = _clean_text(driver.get("direction"))
    if direction.lower() in {"up", "increase", "increased", "positive"}:
        patient_direction = "raising concern"
    elif direction.lower() in {"down", "decrease", "decreased", "negative"}:
        patient_direction = "lowering concern"
    else:
        patient_direction = "important to interpret"
    return {
        "feature_name": _clean_text(driver.get("feature_name")),
        "label": label,
        "direction": direction,
        "patient_direction": patient_direction,
        "impact": round(_driver_impact(driver), 4),
        "feature_value": driver.get("feature_value"),
        "explanation": _clean_text(driver.get("explanation")),
    }


class MLRiskInterpretationAgent:
    """Turns model predictions and SHAP-style drivers into readable clinical context."""

    name = "ml_risk_interpretation_agent"

    def run(self, ml_predictions: dict[str, Any] | None) -> dict[str, Any]:
        ml_data = ml_predictions if isinstance(ml_predictions, dict) else {}
        risk_score = _normalize_probability(
            ml_data.get("overall_risk"),
            _normalize_probability(ml_data.get("risk_score")),
        )
        risk_level = _normalize_risk_level(
            ml_data.get("risk_level") or ml_data.get("ml_risk_level"),
            score=risk_score,
        )
        condition_risks = _coerce_condition_risks(ml_data)

        raw_drivers = ml_data.get("shap_drivers") or ml_data.get("drivers") or ml_data.get("factors") or []
        drivers = [
            _normalize_driver(driver)
            for driver in raw_drivers
            if isinstance(driver, dict)
        ]
        drivers.sort(key=lambda item: item["impact"], reverse=True)
        drivers = drivers[:5]

        if not ml_data:
            interpretation = "I do not have enough recent trend data for that part, so your symptoms, vitals, and labs matter most."
        elif risk_level == "HIGH":
            interpretation = "Your recent health data shows a pattern that deserves closer attention alongside your current symptoms."
        elif risk_level == "MEDIUM":
            interpretation = "Your recent health data looks somewhat watchful and should be interpreted with your symptoms."
        else:
            interpretation = "Your recent health data looks generally stable, though symptoms and abnormal readings can still change the priority."

        if drivers:
            driver_labels = [driver["label"].lower() for driver in drivers[:2]]
            if len(driver_labels) == 1:
                interpretation = f"{interpretation} The strongest data pattern is recent {driver_labels[0]}."
            else:
                interpretation = f"{interpretation} The strongest data patterns are recent {driver_labels[0]} and {driver_labels[1]}."

        recommendations = []
        for item in ml_data.get("recommendations") or []:
            if isinstance(item, dict):
                text = _clean_text(item.get("detail") or item.get("description") or item.get("title"))
            else:
                text = _clean_text(item)
            if text:
                recommendations.append(text)

        return {
            "agent": self.name,
            "available": bool(ml_data),
            "risk_level": risk_level,
            "risk_score": risk_score,
            "condition_risks": condition_risks,
            "top_drivers": drivers,
            "interpretation": interpretation,
            "recommendations": recommendations[:4],
            "prediction_id": ml_data.get("prediction_id"),
            "health_score": _safe_float(ml_data.get("health_score")),
            "confidence": _normalize_probability(ml_data.get("confidence"), risk_score),
        }


def interpret_ml_risk(ml_predictions: dict[str, Any] | None) -> dict[str, Any]:
    return MLRiskInterpretationAgent().run(ml_predictions)
