from __future__ import annotations

import re
from typing import Any, Awaitable, Callable


IntentFallback = Callable[[str, list[dict[str, Any]], dict[str, Any]], Awaitable[dict[str, Any] | None]]


SOCIAL_PATTERNS: dict[str, tuple[str, ...]] = {
    "greeting": ("hi", "hello", "hey", "good morning", "good evening", "good afternoon", "what's up", "whats up"),
    "acknowledgement": ("okay", "ok", "got it", "hmm", "alright", "sure", "noted", "makes sense", "understood"),
    "gratitude": ("thanks", "thank you", "appreciate it", "thx", "thankyou"),
    "farewell": ("bye", "goodbye", "see you", "talk later", "catch you later"),
}

CASUAL_PATTERNS = (
    "how does this work",
    "tell me more",
    "interesting",
    "what can you do",
    "what do you help with",
)

CLARIFICATION_PATTERNS = (
    "what do you mean",
    "can you explain",
    "sorry?",
    "sorry",
    "come again",
    "i don't understand",
)

FOLLOWUP_PATTERNS = (
    "and then",
    "what about",
    "why",
    "how so",
    "what next",
    "is that normal",
)

ONBOARDING_PATTERNS = (
    "how do i start",
    "how do i begin",
    "what can you do",
    "how can you help",
)

NAVIGATION_PATTERNS = (
    "where do i find",
    "how do i upload",
    "where can i upload",
    "where is",
    "how do i view",
)

REPORT_PATTERNS = (
    "analyze this report",
    "analyse this report",
    "lab report",
    "blood report",
    "blood test",
    "scan report",
    "medical report",
    "test result",
    "pdf report",
    "upload report",
)

RISK_PATTERNS = (
    "risk score",
    "risk level",
    "what does this mean",
    "explain my risk",
    "explain the risk",
)

RECOMMENDATION_PATTERNS = (
    "what should i do",
    "any advice",
    "what do you recommend",
    "next step",
    "what now",
)

EMOTIONAL_PATTERNS = (
    "i'm worried",
    "i am worried",
    "i'm scared",
    "i am scared",
    "i'm anxious",
    "i am anxious",
    "i'm stressed",
    "i am stressed",
    "i'm afraid",
    "this is stressing me out",
)

HEALTH_EDUCATION_PATTERNS = (
    "what is",
    "how does blood pressure work",
    "how does diabetes work",
    "what causes",
    "what happens when",
)

DIAGNOSIS_PATTERNS = (
    "diagnosed with",
    "i have diabetes",
    "i have hypertension",
    "i have asthma",
    "i have pcos",
    "i have thyroid",
    "i have anemia",
)

BODY_PARTS = (
    "chest",
    "head",
    "stomach",
    "abdomen",
    "back",
    "arm",
    "leg",
    "throat",
    "neck",
    "shoulder",
    "heart",
    "lung",
)

SYMPTOM_WORDS = (
    "pain",
    "hurts",
    "ache",
    "pressure",
    "dizzy",
    "dizziness",
    "headache",
    "fever",
    "cough",
    "nausea",
    "vomiting",
    "breathless",
    "shortness of breath",
    "can't breathe",
    "cannot breathe",
    "palpitations",
    "rash",
    "swelling",
    "fatigue",
    "weakness",
)

EMERGENCY_PATTERNS = (
    "can't breathe",
    "cannot breathe",
    "crushing chest pain",
    "numb arm",
    "i think i'm having a stroke",
    "i think i am having a stroke",
    "i think i'm having a heart attack",
    "i think i am having a heart attack",
    "unbearable",
    "can't move",
    "cannot move",
    "stroke symptoms",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(text: str) -> str:
    lowered = _clean_text(text).lower()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def _recent_user_text(conversation_history: list[dict[str, Any]] | None) -> str:
    parts: list[str] = []
    for item in (conversation_history or [])[-4:]:
        if not isinstance(item, dict):
            continue
        if _normalize(item.get("role")) != "user":
            continue
        content = _clean_text(item.get("content"))
        if content:
            parts.append(content)
    return _normalize(" ".join(parts))


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    for phrase in phrases:
        if " " in phrase:
            if phrase in text:
                return True
            continue
        if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text):
            return True
    return False


def _has_medical_context(
    conversation_history: list[dict[str, Any]] | None,
    user_context: dict[str, Any] | None,
) -> bool:
    recent_text = _recent_user_text(conversation_history)
    if _contains_any(recent_text, BODY_PARTS + SYMPTOM_WORDS + REPORT_PATTERNS + RISK_PATTERNS):
        return True
    context = user_context if isinstance(user_context, dict) else {}
    for key in ("recent_symptoms", "symptoms_history"):
        if isinstance(context.get(key), list) and context.get(key):
            return True
    conversation_state = context.get("conversation_state") if isinstance(context.get("conversation_state"), dict) else {}
    return bool(conversation_state.get("follow_up_pending"))


def _social_intent(text: str) -> tuple[str, float] | None:
    if len(text.split()) > 5:
        return None
    for intent, phrases in SOCIAL_PATTERNS.items():
        if text in phrases or _contains_any(text, phrases):
            return intent, 0.98
    return None


async def _fallback_intent(
    text: str,
    conversation_history: list[dict[str, Any]] | None,
    user_context: dict[str, Any] | None,
    llm_fallback: IntentFallback | None,
) -> tuple[str, float] | None:
    if llm_fallback is None:
        return None
    payload = await llm_fallback(text, conversation_history or [], user_context or {})
    if not isinstance(payload, dict):
        return None
    intent = _normalize(payload.get("intent"))
    confidence = payload.get("confidence")
    if not intent:
        return None
    try:
        numeric_confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        numeric_confidence = 0.5
    return intent, numeric_confidence


def _mode_for_intent(
    intent: str,
    *,
    has_medical_context: bool,
) -> str:
    if intent == "report_analysis":
        return "expert"
    if intent in {"symptom_report", "emergency_concern", "recommendation_request", "risk_explanation", "health_education", "emotional_support"}:
        return "medical"
    if intent == "followup_question" and has_medical_context:
        return "medical"
    return "casual"


async def classify_intent(
    user_message: str,
    conversation_history: list[dict[str, Any]] | None = None,
    user_context: dict[str, Any] | None = None,
    *,
    llm_fallback: IntentFallback | None = None,
) -> dict[str, Any]:
    text = _normalize(user_message)
    has_medical_context = _has_medical_context(conversation_history, user_context)

    social = _social_intent(text)
    if social:
        intent, confidence = social
        return {"intent": intent, "confidence": confidence, "mode": "casual"}

    if _contains_any(text, EMERGENCY_PATTERNS):
        return {"intent": "emergency_concern", "confidence": 0.99, "mode": "medical"}

    if _contains_any(text, REPORT_PATTERNS):
        return {"intent": "report_analysis", "confidence": 0.92, "mode": "expert"}

    if "risk score" in text or _contains_any(text, RISK_PATTERNS):
        return {"intent": "risk_explanation", "confidence": 0.9, "mode": "medical"}

    if _contains_any(text, ONBOARDING_PATTERNS):
        return {"intent": "onboarding_help", "confidence": 0.88, "mode": "casual"}

    if _contains_any(text, NAVIGATION_PATTERNS):
        return {"intent": "navigation_help", "confidence": 0.86, "mode": "casual"}

    if _contains_any(text, RECOMMENDATION_PATTERNS):
        return {"intent": "recommendation_request", "confidence": 0.88, "mode": "medical"}

    if _contains_any(text, EMOTIONAL_PATTERNS):
        return {"intent": "emotional_support", "confidence": 0.84, "mode": "medical"}

    if _contains_any(text, FOLLOWUP_PATTERNS):
        mode = _mode_for_intent("followup_question", has_medical_context=has_medical_context)
        return {"intent": "followup_question", "confidence": 0.76, "mode": mode}

    if _contains_any(text, CLARIFICATION_PATTERNS):
        mode = "medical" if has_medical_context else "casual"
        return {"intent": "clarification", "confidence": 0.82, "mode": mode}

    if _contains_any(text, CASUAL_PATTERNS):
        return {"intent": "casual_chat", "confidence": 0.8, "mode": "casual"}

    if any(text.startswith(prefix) for prefix in ("what is ", "what's ", "how does ", "how do ")) and _contains_any(text, HEALTH_EDUCATION_PATTERNS + BODY_PARTS + ("diabetes", "blood pressure", "hypertension", "cholesterol", "asthma")):
        return {"intent": "health_education", "confidence": 0.82, "mode": "medical"}

    if _contains_any(text, DIAGNOSIS_PATTERNS):
        return {"intent": "symptom_report", "confidence": 0.8, "mode": "medical"}

    if _contains_any(text, BODY_PARTS) and _contains_any(text, SYMPTOM_WORDS):
        return {"intent": "symptom_report", "confidence": 0.9, "mode": "medical"}

    if _contains_any(text, SYMPTOM_WORDS):
        return {"intent": "symptom_report", "confidence": 0.78, "mode": "medical"}

    fallback = await _fallback_intent(text, conversation_history, user_context, llm_fallback)
    if fallback:
        intent, confidence = fallback
        return {
            "intent": intent,
            "confidence": confidence,
            "mode": _mode_for_intent(intent, has_medical_context=has_medical_context),
        }

    default_intent = "followup_question" if has_medical_context else "casual_chat"
    return {
        "intent": default_intent,
        "confidence": 0.45,
        "mode": _mode_for_intent(default_intent, has_medical_context=has_medical_context),
    }
