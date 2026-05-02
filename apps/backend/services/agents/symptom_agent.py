from __future__ import annotations

import re
from typing import Any

from services.clinical_analysis_service import ClinicalAnalysisService


SYMPTOM_ALIASES = {
    "can't breathe": "shortness of breath",
    "cannot breathe": "shortness of breath",
    "difficulty breathing": "shortness of breath",
    "trouble breathing": "shortness of breath",
    "breathing difficulty": "shortness of breath",
    "chest pressure": "chest pain",
    "pressure in chest": "chest pain",
    "tightness in chest": "chest pain",
    "heart racing": "palpitations",
    "racing heart": "palpitations",
    "irregular heartbeat": "palpitations",
    "lightheaded": "dizziness",
    "light-headed": "dizziness",
    "vertigo": "dizziness",
    "stomach pain": "abdominal pain",
    "throwing up": "vomiting",
    "loose stools": "diarrhea",
    "wheeze": "wheezing",
}

RED_FLAG_PATTERNS = {
    "chest pain": "Chest pain can be a cardiovascular red flag, especially if new, severe, exertional, or paired with breathlessness, sweating, dizziness, or fainting.",
    "chest pressure": "Chest pressure can be a cardiovascular red flag.",
    "shortness of breath": "Shortness of breath can be urgent when severe, new, or present at rest.",
    "severe breathlessness": "Severe breathlessness can require urgent evaluation.",
    "can't breathe": "Severe breathing difficulty can require urgent evaluation.",
    "cannot breathe": "Severe breathing difficulty can require urgent evaluation.",
    "fainting": "Fainting can indicate a circulation, rhythm, neurologic, or metabolic issue.",
    "fainted": "Fainting can indicate a circulation, rhythm, neurologic, or metabolic issue.",
    "passed out": "Passing out can indicate a circulation, rhythm, neurologic, or metabolic issue.",
    "one sided weakness": "One-sided weakness can be a stroke warning symptom.",
    "slurred speech": "Slurred speech can be a stroke warning symptom.",
    "severe bleeding": "Severe bleeding needs urgent care.",
}

HIGH_SEVERITY_TERMS = (
    "severe",
    "worst",
    "crushing",
    "unbearable",
    "can't breathe",
    "cannot breathe",
    "passed out",
    "fainted",
    "fainting",
    "new weakness",
    "slurred speech",
    "severe bleeding",
)

MODERATE_SEVERITY_TERMS = (
    "moderate",
    "worse",
    "worsening",
    "persistent",
    "recurrent",
    "keeps happening",
)

LOW_SEVERITY_TERMS = ("mild", "slight", "minor", "occasional")


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


def _dedupe(items: list[str], *, limit: int | None = None) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _clean_text(item)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        merged.append(text)
        if limit and len(merged) >= limit:
            break
    return merged


def _history_user_text(conversation_history: list[dict[str, Any]] | None) -> str:
    parts = []
    for item in conversation_history or []:
        if not isinstance(item, dict):
            continue
        if _clean_text(item.get("role")).lower() != "user":
            continue
        content = _clean_text(item.get("content"))
        if content:
            parts.append(content[:800])
    return " ".join(parts[-3:])


def _extract_history_symptoms(clinical_history: dict[str, Any] | None) -> list[str]:
    if not isinstance(clinical_history, dict):
        return []
    analysis = clinical_history.get("analysis") if isinstance(clinical_history.get("analysis"), dict) else {}
    return _coerce_list(analysis.get("symptoms"))


def _severity_from_text(text: str, symptoms: list[str]) -> tuple[str, float, list[str]]:
    lowered = text.lower()
    reasons: list[str] = []
    score = 0.25

    numeric_match = re.search(r"\b(10|[1-9])\s*/\s*10\b", lowered)
    if numeric_match:
        numeric = int(numeric_match.group(1))
        score = max(score, numeric / 10)
        reasons.append(f"Self-reported severity {numeric}/10.")

    if any(term in lowered for term in HIGH_SEVERITY_TERMS):
        score = max(score, 0.85)
        reasons.append("High-severity wording or red-flag wording is present.")
    elif any(term in lowered for term in MODERATE_SEVERITY_TERMS):
        score = max(score, 0.55)
        reasons.append("Persistent or worsening symptom language is present.")
    elif any(term in lowered for term in LOW_SEVERITY_TERMS):
        score = max(score, 0.25)
        reasons.append("Mild symptom language is present.")

    normalized = {item.lower() for item in symptoms}
    if "chest pain" in normalized and normalized.intersection({"shortness of breath", "breathlessness", "dizziness", "palpitations"}):
        score = max(score, 0.9)
        reasons.append("Chest symptoms are paired with another concerning symptom.")
    elif "chest pain" in normalized:
        score = max(score, 0.75)
        reasons.append("Chest pain is present.")
    if normalized.intersection({"fainting", "passed out"}):
        score = max(score, 0.9)

    if score >= 0.8:
        return "high", round(score, 2), reasons
    if score >= 0.45:
        return "medium", round(score, 2), reasons
    return "low", round(score, 2), reasons or ["No high-severity wording was detected."]


class SymptomAnalysisAgent:
    """Extracts structured symptoms, severity, and likely body-system categories."""

    name = "symptom_analysis_agent"

    def run(
        self,
        query: str,
        *,
        conversation_history: list[dict[str, Any]] | None = None,
        clinical_history: dict[str, Any] | None = None,
        known_symptoms: list[str] | None = None,
    ) -> dict[str, Any]:
        current_query = _clean_text(query)
        combined_text = " ".join(
            part
            for part in (_history_user_text(conversation_history), current_query)
            if part
        )
        lowered = combined_text.lower()

        symptom_names: list[str] = []
        sources: dict[str, str] = {}
        for symptom in ClinicalAnalysisService.SYMPTOM_SYSTEM_MAP:
            if symptom in lowered:
                symptom_names.append(symptom)
                sources[symptom] = "query"
        for alias, canonical in SYMPTOM_ALIASES.items():
            if alias in lowered:
                symptom_names.append(canonical)
                sources[canonical] = "query_alias"

        for symptom in _extract_history_symptoms(clinical_history):
            symptom_names.append(symptom)
            sources.setdefault(symptom, "clinical_history")
        for symptom in _coerce_list(known_symptoms):
            symptom_names.append(symptom)
            sources.setdefault(symptom, "known_context")

        symptom_names = _dedupe(symptom_names, limit=8)
        structured_symptoms = []
        categories: list[str] = []
        for symptom in symptom_names:
            lowered_symptom = symptom.lower()
            category = ClinicalAnalysisService.SYMPTOM_SYSTEM_MAP.get(lowered_symptom)
            if category is None:
                for keyword, mapped_category in ClinicalAnalysisService.SYMPTOM_SYSTEM_MAP.items():
                    if keyword in lowered_symptom:
                        category = mapped_category
                        break
            category = category or "general"
            categories.append(category)
            structured_symptoms.append(
                {
                    "name": symptom,
                    "category": category,
                    "source": sources.get(symptom) or sources.get(lowered_symptom) or "query",
                }
            )

        red_flags = [
            {"trigger": pattern, "reason": reason}
            for pattern, reason in RED_FLAG_PATTERNS.items()
            if pattern in lowered
        ]
        severity, severity_score, severity_reasons = _severity_from_text(combined_text, symptom_names)

        return {
            "agent": self.name,
            "structured_symptoms": structured_symptoms,
            "symptom_names": symptom_names,
            "severity": severity,
            "severity_score": severity_score,
            "severity_reasons": severity_reasons,
            "possible_categories": _dedupe(categories, limit=5),
            "red_flags": red_flags,
            "raw_query": current_query,
        }


def analyze_symptoms(query: str, **kwargs: Any) -> dict[str, Any]:
    return SymptomAnalysisAgent().run(query, **kwargs)
