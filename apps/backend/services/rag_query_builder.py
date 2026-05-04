from __future__ import annotations

import re
from typing import Any


MAX_QUERY_WORDS = 24
DEFAULT_CONDITION = "general preventive care"
GUIDELINE_TERMS = ("prevention", "lifestyle", "monitoring", "early warning", "guidelines", "WHO", "CDC")


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("_", " ").strip().lower()
    text = re.sub(r"[^a-z0-9%./\s-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _dedupe_terms(terms: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        cleaned = _clean_text(term)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return deduped


def _word_count(terms: list[str]) -> int:
    return len(" ".join(terms).split())


def _trim_terms(terms: list[str], *, max_words: int = MAX_QUERY_WORDS) -> list[str]:
    trimmed: list[str] = []
    for term in terms:
        candidate = trimmed + [term]
        if _word_count(candidate) > max_words:
            continue
        trimmed.append(term)
    return trimmed


def _normalize_probability(value: Any) -> float | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    if numeric > 1:
        numeric /= 100.0
    return max(0.0, min(1.0, numeric))


def _top_prediction(context: dict[str, Any]) -> dict[str, Any]:
    predictions = context.get("risk_predictions")
    if not isinstance(predictions, list):
        return {"condition": DEFAULT_CONDITION, "risk": 0.0, "confidence": 0.0}

    valid_predictions: list[dict[str, Any]] = []
    for item in predictions:
        if not isinstance(item, dict):
            continue
        risk = _normalize_probability(item.get("risk"))
        condition = _clean_text(item.get("condition"))
        if risk is None or not condition:
            continue
        valid_predictions.append(
            {
                "condition": condition,
                "risk": risk,
                "confidence": _normalize_probability(item.get("confidence")) or 0.0,
            }
        )

    if not valid_predictions:
        return {"condition": DEFAULT_CONDITION, "risk": 0.0, "confidence": 0.0}
    return max(valid_predictions, key=lambda item: (item["risk"], item["confidence"]))


def _parse_bp(value: Any) -> tuple[float | None, float | None]:
    if not value:
        return None, None
    match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", str(value))
    if not match:
        return None, None
    return _safe_float(match.group(1)), _safe_float(match.group(2))


def _abnormal_vitals(vitals: dict[str, Any]) -> list[tuple[str, str]]:
    if not isinstance(vitals, dict):
        return []

    abnormal: list[tuple[str, str]] = []
    steps = _safe_float(vitals.get("steps"))
    heart_rate = _safe_float(vitals.get("heart_rate"))
    sleep = _safe_float(vitals.get("sleep"))
    spo2 = _safe_float(vitals.get("spo2"))
    glucose = _safe_float(vitals.get("glucose"))
    temperature = _safe_float(vitals.get("temperature"))
    systolic, diastolic = _parse_bp(vitals.get("blood_pressure"))

    if heart_rate is not None and heart_rate < 60:
        abnormal.append(("heart_rate", "low heart rate"))
    elif heart_rate is not None and heart_rate > 100:
        abnormal.append(("heart_rate", "high heart rate"))

    if systolic is not None and diastolic is not None:
        if systolic >= 130 or diastolic >= 80:
            abnormal.append(("blood_pressure", "high blood pressure"))
        elif systolic < 90 or diastolic < 60:
            abnormal.append(("blood_pressure", "low blood pressure"))

    if glucose is not None and glucose < 70:
        abnormal.append(("glucose", "low glucose"))
    elif glucose is not None and glucose >= 126:
        abnormal.append(("glucose", "high glucose"))

    if spo2 is not None and spo2 < 95:
        abnormal.append(("spo2", "low oxygen saturation"))

    if temperature is not None and temperature >= 37.8:
        abnormal.append(("temperature", "fever"))
    elif temperature is not None and temperature < 36:
        abnormal.append(("temperature", "low temperature"))

    if sleep is not None and sleep < 6:
        abnormal.append(("sleep", "short sleep"))
    if steps is not None and steps < 4000:
        abnormal.append(("steps", "low activity"))

    priority = {
        "blood_pressure": 0,
        "heart_rate": 1,
        "glucose": 2,
        "spo2": 3,
        "temperature": 4,
        "sleep": 5,
        "steps": 6,
    }
    return sorted(abnormal, key=lambda item: priority.get(item[0], 99))


def _trend_terms(trends: dict[str, Any]) -> list[str]:
    if not isinstance(trends, dict):
        return []

    labels = {
        "steps_trend": "steps",
        "heart_rate_trend": "heart rate",
        "bp_trend": "blood pressure",
        "glucose_trend": "glucose",
    }
    terms: list[str] = []
    for key, label in labels.items():
        value = _clean_text(trends.get(key))
        if value in {"increasing", "decreasing"}:
            terms.append(f"{value} {label}")
    return terms


def _symptom_terms(context: dict[str, Any]) -> list[str]:
    symptoms = context.get("symptoms")
    if not isinstance(symptoms, list):
        return []
    return [_clean_text(symptom) for symptom in symptoms if _clean_text(symptom)][:3]


def _severity(top_prediction: dict[str, Any], abnormal_vitals: list[tuple[str, str]], symptoms: list[str]) -> str:
    risk = float(top_prediction.get("risk") or 0.0)
    abnormal_terms = {term for _, term in abnormal_vitals}
    urgent_symptom = any(
        symptom in {"chest pain", "shortness of breath", "fainting", "confusion", "severe dizziness"}
        for symptom in symptoms
    )

    if risk >= 0.7 or urgent_symptom or {"low oxygen saturation", "high blood pressure"} & abnormal_terms:
        return "high"
    if risk >= 0.4 or abnormal_vitals or symptoms:
        return "medium"
    return "low"


def build_rag_query(context: dict[str, Any] | None) -> dict[str, Any]:
    """
    Convert structured recommendation context into a concise medical RAG query.

    The builder is intentionally rule-based: no LLM call, no database access.
    """
    payload = context if isinstance(context, dict) else {}
    top_prediction = _top_prediction(payload)
    condition = top_prediction["condition"] or DEFAULT_CONDITION
    vitals = payload.get("vitals") if isinstance(payload.get("vitals"), dict) else {}
    abnormal = _abnormal_vitals(vitals)
    symptoms = _symptom_terms(payload)
    trends = _trend_terms(payload.get("trends") if isinstance(payload.get("trends"), dict) else {})
    severity = _severity(top_prediction, abnormal, symptoms)

    terms = _dedupe_terms(
        [
            condition,
            *symptoms,
            *(term for _, term in abnormal[:3]),
            *trends[:2],
            *GUIDELINE_TERMS,
        ]
    )
    terms = _trim_terms(terms)
    query = " ".join(terms).strip() or DEFAULT_CONDITION

    return {
        "query": query,
        "filters": {
            "condition": condition,
            "severity": severity,
        },
    }
