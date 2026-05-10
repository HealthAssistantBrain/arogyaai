from __future__ import annotations

import re
from typing import Any


ANXIETY_PATTERNS = (
    "worried",
    "scared",
    "afraid",
    "panic",
    "anxious",
    "serious",
    "dangerous",
    "should i be worried",
)
CONFUSION_PATTERNS = (
    "what does this mean",
    "confused",
    "not sure",
    "i don't understand",
    "can you explain",
    "is this normal",
)
URGENCY_PATTERNS = (
    "right now",
    "immediately",
    "urgent",
    "can't breathe",
    "cannot breathe",
    "severe",
    "sudden",
    "getting worse",
    "worsening",
    "asap",
)
FRUSTRATION_PATTERNS = (
    "still happening",
    "again",
    "no one knows",
    "nothing helped",
    "frustrated",
    "tired of",
    "keeps happening",
)
CURIOSITY_PATTERNS = (
    "why",
    "how",
    "explain",
    "what is causing",
    "could this be",
    "help me understand",
)
STRESS_PATTERNS = (
    "stressed",
    "overwhelmed",
    "tense",
    "burned out",
    "sleep deprived",
    "not sleeping",
)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _score_hits(text: str, patterns: tuple[str, ...], *, weight: float = 0.18) -> float:
    lowered = text.lower()
    hits = sum(1 for pattern in patterns if pattern in lowered)
    punctuation_bonus = 0.0
    if "!" in text:
        punctuation_bonus += 0.08
    if text.isupper() and text:
        punctuation_bonus += 0.1
    return min(1.0, (hits * weight) + punctuation_bonus)


def _recent_user_text(history: list[dict[str, Any]] | None) -> str:
    recent: list[str] = []
    for item in _safe_list(history)[-4:]:
        if not isinstance(item, dict):
            continue
        if str(item.get("role") or "").lower() == "user":
            content = _safe_text(item.get("content"))
            if content:
                recent.append(content)
    return " ".join(recent)


def infer_emotional_context(
    *,
    query: str,
    conversation_history: list[dict[str, Any]] | None = None,
    conversation_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = conversation_state if isinstance(conversation_state, dict) else {}
    recent_text = _recent_user_text(conversation_history)
    combined = " ".join(part for part in (recent_text, _safe_text(query)) if part).strip()

    anxiety = _score_hits(combined, ANXIETY_PATTERNS, weight=0.22)
    confusion = _score_hits(combined, CONFUSION_PATTERNS, weight=0.24)
    urgency = _score_hits(combined, URGENCY_PATTERNS, weight=0.24)
    frustration = _score_hits(combined, FRUSTRATION_PATTERNS, weight=0.2)
    curiosity = _score_hits(combined, CURIOSITY_PATTERNS, weight=0.14)
    stress = _score_hits(combined, STRESS_PATTERNS, weight=0.22)

    if len(_safe_text(query).split()) <= 4 and "?" in query:
        confusion = min(1.0, confusion + 0.08)
    if len(_safe_text(query).split()) >= 25:
        curiosity = min(1.0, curiosity + 0.1)
    if state.get("follow_up_pending"):
        urgency = min(1.0, urgency + 0.06)
    if anxiety > 0 and urgency >= 0.45:
        anxiety = min(1.0, anxiety + 0.12)
    if "really worried" in combined.lower():
        anxiety = min(1.0, anxiety + 0.08)
    if len(_safe_list(state.get("recent_emotions"))) >= 2:
        anxiety = min(1.0, anxiety + 0.04)

    reassurance_need = min(1.0, max(anxiety, stress, frustration * 0.8))
    scores = {
        "anxiety": round(anxiety, 2),
        "confusion": round(confusion, 2),
        "urgency": round(urgency, 2),
        "frustration": round(frustration, 2),
        "reassurance_need": round(reassurance_need, 2),
        "curiosity": round(curiosity, 2),
        "stress": round(stress, 2),
    }
    dominant_emotion = max(scores, key=scores.get) if any(scores.values()) else "neutral"

    explanation_depth = "balanced"
    if confusion >= 0.55 or reassurance_need >= 0.7:
        explanation_depth = "simple"
    elif curiosity >= 0.45 and confusion < 0.4:
        explanation_depth = "layered"

    pacing = "steady"
    if urgency >= 0.7:
        pacing = "rapid"
    elif reassurance_need >= 0.65:
        pacing = "slow"

    follow_up_intensity = "moderate"
    if urgency >= 0.75:
        follow_up_intensity = "high"
    elif reassurance_need >= 0.7:
        follow_up_intensity = "gentle"

    tone = "calm"
    if urgency >= 0.8:
        tone = "direct"
    elif reassurance_need >= 0.4:
        tone = "reassuring"
    elif curiosity >= 0.45:
        tone = "educational"

    indicators: list[str] = []
    if anxiety >= 0.4:
        indicators.append("anxiety_language")
    if confusion >= 0.4:
        indicators.append("clarity_request")
    if urgency >= 0.5:
        indicators.append("urgency_language")
    if frustration >= 0.4:
        indicators.append("repeat_concern")
    if stress >= 0.4:
        indicators.append("stress_signal")
    if re.search(r"\b\d+/10\b", combined.lower()):
        indicators.append("severity_rating_present")

    return {
        **scores,
        "dominant_emotion": dominant_emotion if scores[dominant_emotion] > 0 else "neutral",
        "stress_indicators": indicators,
        "adaptation": {
            "tone": tone,
            "explanation_depth": explanation_depth,
            "pacing": pacing,
            "follow_up_intensity": follow_up_intensity,
            "reassurance_level": "high" if reassurance_need >= 0.65 else "moderate" if reassurance_need >= 0.35 else "light",
        },
    }
