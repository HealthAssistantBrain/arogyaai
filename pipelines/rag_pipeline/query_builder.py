from __future__ import annotations

from typing import Any

from .schemas import ShapSignal


_FEATURE_MAP: dict[str, dict[str, str]] = {
    "bmi": {
        "display_name": "BMI",
        "category": "diabetes",
        "hint": "high bmi body mass index insulin resistance weight",
    },
    "activity_level": {
        "display_name": "Activity level",
        "category": "lifestyle",
        "hint": "low activity sedentary exercise physical inactivity cardiovascular risk",
    },
    "activity_score": {
        "display_name": "Activity score",
        "category": "lifestyle",
        "hint": "low activity conditioning daily movement exercise cardiovascular fitness",
    },
    "steps_avg_7d": {
        "display_name": "Average daily steps",
        "category": "lifestyle",
        "hint": "low steps walking inactivity sedentary cardiovascular risk",
    },
    "sleep_efficiency": {
        "display_name": "Sleep efficiency",
        "category": "sleep",
        "hint": "poor sleep efficiency fragmented sleep metabolic health insulin sensitivity",
    },
    "sleep_score": {
        "display_name": "Sleep score",
        "category": "sleep",
        "hint": "poor sleep quality metabolic health recovery insulin resistance",
    },
    "sleep_duration": {
        "display_name": "Sleep duration",
        "category": "sleep",
        "hint": "short sleep sleep deficiency metabolic health glucose regulation",
    },
    "avg_rhr": {
        "display_name": "Resting heart rate",
        "category": "lifestyle",
        "hint": "high resting heart rate deconditioning stress cardiovascular fitness",
    },
    "hr_mean_7d": {
        "display_name": "Average heart rate",
        "category": "lifestyle",
        "hint": "elevated heart rate recovery stress cardiovascular conditioning",
    },
    "avg_hrv": {
        "display_name": "Heart-rate variability",
        "category": "sleep",
        "hint": "low heart rate variability stress recovery autonomic balance sleep",
    },
    "systolic_bp": {
        "display_name": "Systolic blood pressure",
        "category": "lifestyle",
        "hint": "high blood pressure hypertension cardiovascular risk metabolic syndrome",
    },
    "diastolic_bp": {
        "display_name": "Diastolic blood pressure",
        "category": "lifestyle",
        "hint": "high blood pressure hypertension vascular risk",
    },
    "cholesterol_proxy": {
        "display_name": "Cholesterol proxy",
        "category": "diabetes",
        "hint": "cholesterol dyslipidemia cardiometabolic risk insulin resistance",
    },
    "age": {
        "display_name": "Age",
        "category": "diabetes",
        "hint": "age related diabetes risk metabolic risk cardiovascular risk",
    },
}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _display_name(feature_name: str) -> str:
    entry = _FEATURE_MAP.get(feature_name, {})
    if entry.get("display_name"):
        return entry["display_name"]
    return feature_name.replace("_", " ").title()


def normalize_shap_inputs(shap_values: list[dict[str, Any]], limit: int = 3) -> list[ShapSignal]:
    normalized: list[ShapSignal] = []
    for item in shap_values:
        feature_name = str(item.get("feature_name") or item.get("feature") or item.get("key") or "").strip()
        if not feature_name:
            continue

        shap_value = _safe_float(item.get("shap_value") or item.get("value") or item.get("contribution"))
        if shap_value is None:
            continue

        abs_shap_value = _safe_float(item.get("abs_shap_value"))
        metadata = _FEATURE_MAP.get(feature_name, {})
        normalized.append(
            ShapSignal(
                feature_name=feature_name,
                display_name=_display_name(feature_name),
                shap_value=float(shap_value),
                abs_shap_value=float(abs_shap_value if abs_shap_value is not None else abs(shap_value)),
                direction="increase" if float(shap_value) >= 0 else "decrease",
                feature_value=_safe_float(
                    item.get("feature_value")
                    if item.get("feature_value") is not None
                    else (item.get("shap_payload") or {}).get("feature_value")
                ),
                category=metadata.get("category", "general"),
                search_hint=metadata.get("hint", feature_name.replace("_", " ")),
            )
        )

    normalized.sort(key=lambda signal: signal.abs_shap_value, reverse=True)
    return normalized[:limit]


def build_query_from_shap(shap_values: list[dict[str, Any]], limit: int = 3) -> dict[str, Any]:
    signals = normalize_shap_inputs(shap_values, limit=limit)
    if not signals:
        return {
            "query": "",
            "signals": [],
            "categories": [],
        }

    query_parts: list[str] = []
    categories: list[str] = []
    for signal in signals:
        query_parts.append(signal.search_hint)
        categories.append(signal.category)

    unique_categories = list(dict.fromkeys(categories))
    return {
        "query": " ".join(query_parts),
        "signals": [signal.as_dict() for signal in signals],
        "categories": unique_categories,
    }
