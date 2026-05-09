from __future__ import annotations

from typing import Any


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    else:
        items = []
    return [_clean_text(item) for item in items if _clean_text(item)]


def _duration_label(duration_value: Any, duration_unit: Any) -> str:
    try:
        value = int(duration_value)
    except (TypeError, ValueError):
        return _clean_text(duration_unit)

    unit = _clean_text(duration_unit).lower() or "days"
    singular = unit[:-1] if unit.endswith("s") else unit
    plural = singular if value == 1 else f"{singular}s"
    return f"{value} {plural}"


def build_symptom_analysis_prompt_payload(
    request_payload: dict[str, Any],
    *,
    feature_payload: dict[str, Any] | None = None,
    recent_reports: list[dict[str, Any]] | None = None,
    recent_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = request_payload if isinstance(request_payload, dict) else {}
    associated_symptoms = _coerce_list(payload.get("associated_symptoms"))
    prompt_context = {
        "provider_hint": "deterministic_fallback",
        "future_model_router": {
            "preferred_reasoning_model": "nvidia_reasoning_placeholder",
            "preferred_summarization_model": "nvidia_summarization_placeholder",
            "personalization_layer": "future_user_context_adapter",
        },
        "patient_input": {
            "chief_complaint": _clean_text(payload.get("chief_complaint")),
            "duration": _duration_label(payload.get("duration_value"), payload.get("duration_unit")),
            "severity": payload.get("severity"),
            "associated_symptoms": associated_symptoms,
            "aggravating_factors": _clean_text(payload.get("aggravating_factors")),
            "relieving_factors": _clean_text(payload.get("relieving_factors")),
            "previous_episodes": _clean_text(payload.get("previous_episodes")),
            "medications": _clean_text(payload.get("medications")),
            "notes": _clean_text(payload.get("notes")),
        },
        "context": {
            "feature_snapshot": feature_payload if isinstance(feature_payload, dict) else {},
            "recent_reports": recent_reports or [],
            "recent_symptom_history": recent_history or [],
        },
        "instructions": [
            "Use cautious, suggestive clinical reasoning.",
            "Do not claim diagnostic certainty or present yourself as a licensed doctor.",
            "Prioritize red-flag detection before differential suggestions.",
            "Return a structured summary, likely causes, urgency, risk indicators, recommendations, and confidence.",
        ],
    }
    return prompt_context
