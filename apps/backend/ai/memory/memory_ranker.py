from __future__ import annotations

from .memory_types import MemoryImportance
from ..safety.clinical_rules import HIGH_RISK_TERMS, EMERGENCY_PATTERNS

_HIGH_RISK_LOWER = {str(term).lower() for term in HIGH_RISK_TERMS}

_IMPORTANCE_KEYWORDS = {
    MemoryImportance.CRITICAL: [
        "chest pain",
        "heart attack",
        "stroke",
        "emergency",
        "unconscious",
        "severe bleeding",
        "anaphylaxis",
        "can't breathe",
        "cannot breathe",
    ],
    MemoryImportance.HIGH: [
        "diabetes",
        "hypertension",
        "blood pressure",
        "kidney",
        "liver",
        "recurring",
        "worsening",
        "high risk",
        "abnormal",
    ],
    MemoryImportance.MEDIUM: [
        "symptom",
        "monitor",
        "blood sugar",
        "cholesterol",
        "weight",
        "sleep",
        "headache",
        "palpitations",
    ],
    MemoryImportance.LOW: [
        "thank you",
        "question about",
        "what is",
        "how are you",
    ],
}


def score_importance_from_text(
    text: str,
    *,
    symptoms: list[str] | None = None,
    has_recommendations: bool = False,
    emotional_intensity: float = 0.0,
) -> MemoryImportance:
    lowered = str(text or "").lower()
    symptoms = symptoms or []

    emergency_keywords = {token.lower() for values in EMERGENCY_PATTERNS.values() for token in values}
    if any(keyword in lowered for keyword in _IMPORTANCE_KEYWORDS[MemoryImportance.CRITICAL]):
        return MemoryImportance.CRITICAL
    if any(keyword in lowered for keyword in emergency_keywords):
        return MemoryImportance.CRITICAL
    if any(keyword in lowered for keyword in _HIGH_RISK_LOWER):
        return MemoryImportance.HIGH

    high_hits = sum(1 for keyword in _IMPORTANCE_KEYWORDS[MemoryImportance.HIGH] if keyword in lowered)
    if high_hits >= 2 or (high_hits >= 1 and has_recommendations):
        return MemoryImportance.HIGH
    if emotional_intensity >= 0.7 or len(symptoms) >= 2:
        return MemoryImportance.HIGH

    if any(keyword in lowered for keyword in _IMPORTANCE_KEYWORDS[MemoryImportance.MEDIUM]) or symptoms:
        return MemoryImportance.MEDIUM
    if any(keyword in lowered for keyword in _IMPORTANCE_KEYWORDS[MemoryImportance.LOW]):
        return MemoryImportance.LOW
    if len(lowered.split()) < 10:
        return MemoryImportance.TRIVIAL
    return MemoryImportance.LOW
