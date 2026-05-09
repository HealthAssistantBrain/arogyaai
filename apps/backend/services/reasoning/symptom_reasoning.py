from __future__ import annotations

from typing import Any

from services.agents.reasoning_agent import reason_clinically
from services.agents.response_agent import generate_response
from services.agents.symptom_agent import analyze_symptoms
from services.clinical_analysis_service import ClinicalAnalysisService


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _dedupe(items: list[str], *, limit: int | None = None) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _clean_text(item)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
        if limit and len(cleaned) >= limit:
            break
    return cleaned


def _duration_label(duration_value: Any, duration_unit: Any) -> str:
    try:
        value = int(duration_value)
    except (TypeError, ValueError):
        return _clean_text(duration_unit)

    unit = _clean_text(duration_unit).lower() or "days"
    singular = unit[:-1] if unit.endswith("s") else unit
    plural = singular if value == 1 else f"{singular}s"
    return f"{value} {plural}"


def _build_query(payload: dict[str, Any]) -> str:
    parts = [
        f"Chief complaint: {_clean_text(payload.get('chief_complaint'))}.",
        f"Duration: {_duration_label(payload.get('duration_value'), payload.get('duration_unit'))}.",
        f"Severity: {payload.get('severity')}/10.",
    ]

    associated = payload.get("associated_symptoms") if isinstance(payload.get("associated_symptoms"), list) else []
    if associated:
        parts.append(f"Associated symptoms: {', '.join(associated[:8])}.")

    for label, key in (
        ("Aggravating factors", "aggravating_factors"),
        ("Relieving factors", "relieving_factors"),
        ("Previous episodes", "previous_episodes"),
        ("Medications taken", "medications"),
        ("Notes", "notes"),
    ):
        text = _clean_text(payload.get(key))
        if text:
            parts.append(f"{label}: {text}.")

    return " ".join(parts)


def _possible_causes(baseline_analysis: dict[str, Any], response_payload: dict[str, Any]) -> list[str]:
    baseline = baseline_analysis.get("possible_conditions") if isinstance(baseline_analysis, dict) else []
    response_causes = response_payload.get("possible_causes") if isinstance(response_payload, dict) else []
    cleaned_response = []
    for item in response_causes or []:
        text = _clean_text(item).removesuffix(".")
        if text.lower().startswith("this could relate to "):
            text = text[21:].strip()
        elif text.lower().startswith("this may fit "):
            text = text[13:].strip()
        if text:
            cleaned_response.append(text[:160])
    return _dedupe(list(baseline or []) + cleaned_response, limit=5)


async def run_symptom_reasoning(
    payload: dict[str, Any],
    *,
    feature_payload: dict[str, Any] | None = None,
    context_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request_payload = payload if isinstance(payload, dict) else {}
    features = feature_payload if isinstance(feature_payload, dict) else {}
    context_data = context_snapshot if isinstance(context_snapshot, dict) else {}

    baseline_analysis = ClinicalAnalysisService.analyze_history(
        {
            "chief_complaint": request_payload.get("chief_complaint"),
            "duration": _duration_label(request_payload.get("duration_value"), request_payload.get("duration_unit")),
            "severity": request_payload.get("severity"),
            "associated_symptoms": request_payload.get("associated_symptoms"),
        },
        feature_payload=features,
        user_age=context_data.get("user_age"),
    )

    query = _build_query(request_payload)
    symptom_signal = analyze_symptoms(
        query,
        known_symptoms=request_payload.get("associated_symptoms"),
        clinical_history=context_data.get("latest_clinical_history"),
    )
    ml_interpretation = {
        "available": False,
        "risk_level": str(baseline_analysis.get("risk_level") or "low").upper(),
        "interpretation": baseline_analysis.get("summary"),
    }
    ml_data = {
        "possible_conditions": baseline_analysis.get("possible_conditions") or [],
    }
    analysis_context = {
        "query": query,
        "symptoms": symptom_signal,
        "ml_interpretation": ml_interpretation,
        "ml_data": ml_data,
        "rag_data": {},
        "vitals": context_data.get("vitals") or {},
        "labs": context_data.get("labs") or {},
        "user_context": {
            "recent_reports": context_data.get("recent_reports") or [],
            "feature_snapshot": features,
        },
    }
    reasoning = reason_clinically(analysis_context)
    response_result = await generate_response(
        {
            **analysis_context,
            "clinical_reasoning": reasoning,
            "safety": context_data.get("safety") or {},
        }
    )
    final_response = response_result.get("final_response") if isinstance(response_result, dict) else {}

    return {
        "query": query,
        "baseline_analysis": baseline_analysis,
        "symptom_signal": symptom_signal,
        "reasoning": reasoning,
        "response": final_response,
        "possible_causes": _possible_causes(baseline_analysis, final_response),
    }
