from __future__ import annotations

from typing import Any


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique_texts(items: list[Any], *, limit: int = 4) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in _safe_list(items):
        if isinstance(item, dict):
            text = _safe_text(
                item.get("summary")
                or item.get("detail")
                or item.get("description")
                or item.get("title")
                or item.get("name")
            )
        else:
            text = _safe_text(item)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def build_continuity_snapshot(
    *,
    user_context: dict[str, Any] | None,
    conversation_history: list[dict[str, Any]] | None = None,
    response_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = user_context if isinstance(user_context, dict) else {}
    state = _safe_dict(context.get("conversation_state"))
    longitudinal = _safe_dict(context.get("longitudinal_summary"))
    response = response_payload if isinstance(response_payload, dict) else {}

    symptom_history = _unique_texts(
        [
            *(_safe_list(context.get("recent_symptoms")) or _safe_list(context.get("symptoms_history"))),
            *(_safe_list(state.get("symptoms_history"))),
        ],
        limit=6,
    )
    prior_recommendations = []
    for item in _safe_list(context.get("recommendation_history"))[:3]:
        if isinstance(item, dict):
            prior_recommendations.append(item.get("summary") or item.get("title"))
        else:
            prior_recommendations.append(item)
    carryover = _unique_texts(
        [
            *(_safe_list(longitudinal.get("recommendation_carryover"))),
            *prior_recommendations,
        ],
        limit=3,
    )
    persistent_issues = _unique_texts(longitudinal.get("persistent_issues"), limit=3)
    recent_assistant_highlights = _unique_texts(state.get("assistant_highlights"), limit=2)
    recent_user_highlights = _unique_texts(state.get("user_highlights"), limit=2)

    reference = ""
    if persistent_issues:
        reference = f"last time you mentioned {persistent_issues[0].lower()}"
    elif symptom_history:
        reference = f"you previously brought up {symptom_history[0].lower()}"
    elif recent_user_highlights:
        reference = f"earlier you said '{recent_user_highlights[0]}'"

    comparison = ""
    major_trends = _safe_list(longitudinal.get("major_trends"))
    if major_trends:
        comparison = f"Compared with earlier context, {major_trends[0].lower()}"

    active_follow_up = []
    for item in _safe_list(response.get("follow_up_questions"))[:2]:
        active_follow_up.append(_safe_text(item))

    return {
        "known_symptoms": symptom_history,
        "persistent_issues": persistent_issues,
        "care_plan_carryover": carryover,
        "assistant_highlights": recent_assistant_highlights,
        "user_highlights": recent_user_highlights,
        "reference": reference,
        "comparison_hint": comparison,
        "follow_up_pending": bool(state.get("follow_up_pending")),
        "recent_emotions": _unique_texts(state.get("recent_emotions"), limit=3),
        "last_persona": _safe_text(state.get("last_persona")),
        "last_follow_up_topics": _unique_texts(state.get("last_follow_up_topics"), limit=3),
        "active_follow_up": _unique_texts(active_follow_up, limit=2),
    }


def build_memory_persistence(
    *,
    response_payload: dict[str, Any] | None,
    emotional_context: dict[str, Any] | None = None,
    persona: dict[str, Any] | None = None,
    continuity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = response_payload if isinstance(response_payload, dict) else {}
    emotion = emotional_context if isinstance(emotional_context, dict) else {}
    continuity = continuity if isinstance(continuity, dict) else {}
    persona_primary = _safe_dict(persona).get("primary") if isinstance(persona, dict) else {}
    dominant = _safe_text(emotion.get("dominant_emotion"), "neutral")

    return {
        "summary": _safe_text(payload.get("summary") or payload.get("message") or payload.get("clinical_summary")),
        "risk_level": _safe_text(payload.get("risk_level")),
        "follow_up_questions": _unique_texts(payload.get("follow_up_questions"), limit=2),
        "recommendations": _unique_texts(payload.get("recommendations"), limit=3),
        "symptoms": _unique_texts(payload.get("symptoms"), limit=4),
        "dominant_emotion": dominant,
        "reassurance_level": _safe_text(_safe_dict(emotion.get("adaptation")).get("reassurance_level")),
        "persona": _safe_text(_safe_dict(persona_primary).get("key")),
        "continuity_reference": _safe_text(continuity.get("reference")),
    }
