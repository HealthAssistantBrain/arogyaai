from __future__ import annotations

import re
from typing import Any


REPETITIVE_PHRASES = (
    ("based on your data", "From the overall pattern"),
    ("it is important to", "It helps to"),
    ("the patient", "you"),
    ("the user", "you"),
    ("please note that", ""),
    ("in conclusion", ""),
)


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_sentence(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    normalized = re.sub(r"^[\-*]\s*", "", normalized)
    normalized = re.sub(r"\s+([,.;:!?])", r"\1", normalized)
    if normalized and normalized[-1] not in ".!?":
        normalized += "."
    if normalized:
        normalized = normalized[0].upper() + normalized[1:]
    return normalized


def _dedupe_sentences(parts: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for part in parts:
        text = _clean_sentence(part)
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            cleaned.append(text)
    return cleaned


def _tone_opening(
    *,
    risk_level: str,
    emotional_context: dict[str, Any],
    continuity: dict[str, Any],
) -> str:
    risk = _safe_text(risk_level, "low").lower()
    dominant = _safe_text(emotional_context.get("dominant_emotion"), "neutral").lower()
    reassurance = _safe_text(_safe_dict(emotional_context.get("adaptation")).get("reassurance_level"), "light").lower()
    reference = _safe_text(continuity.get("reference"))

    if risk == "high":
        base = "This pattern needs a careful and fairly prompt response."
    elif risk == "medium":
        base = "This deserves a closer look, even though it is not automatically an emergency."
    else:
        base = "What you are describing sounds worth watching carefully."

    if dominant in {"anxiety", "anxious", "stressed"} or reassurance == "high":
        base = "I can see why this feels worrying, so let me walk through it clearly."
    elif dominant in {"confusion", "confused", "overwhelmed"}:
        base = "There is a lot here, so I will keep this straightforward."
    elif dominant in {"frustration"}:
        base = "Since this has been bothering you, it makes sense to narrow it down step by step."

    if reference and risk not in {"high", "emergency"}:
        return f"{base} This also connects with {reference}."
    return base


def _transition(persona: dict[str, Any], emotional_context: dict[str, Any]) -> str:
    primary = _safe_dict(persona.get("primary"))
    style = _safe_text(primary.get("transition_style"), "clinical but human").lower()
    tone = _safe_text(_safe_dict(emotional_context.get("adaptation")).get("tone"), "calm")
    if "grounding" in style or tone == "reassuring":
        return "What stands out most is this."
    if tone == "direct":
        return "The key point is this."
    return "Here is how I would interpret it."


def _build_message(
    *,
    workflow: str,
    payload: dict[str, Any],
    persona: dict[str, Any],
    emotional_context: dict[str, Any],
    continuity: dict[str, Any],
) -> str:
    opening = _tone_opening(
        risk_level=_safe_text(payload.get("risk_level")),
        emotional_context=emotional_context,
        continuity=continuity,
    )
    transition = _transition(persona, emotional_context)
    interpretation = _safe_text(
        payload.get("clinical_interpretation")
        or payload.get("clinical_insight")
        or payload.get("interpretation")
        or payload.get("summary")
    )
    causes = _safe_list(payload.get("possible_causes"))[:2]
    recommendations = _safe_list(payload.get("recommendations"))[:2]
    monitor = _safe_list(payload.get("what_to_monitor"))[:1]
    follow_up = _safe_list(payload.get("follow_up_questions"))[:2]
    safety = _safe_list(payload.get("safety_notes"))[:1]

    first_paragraph = " ".join(
        _dedupe_sentences(
            [
                opening,
                transition,
                interpretation,
            ]
        )[:3]
    )

    second_bits: list[str] = []
    if causes:
        second_bits.append("Possible explanations I would keep in mind include " + ", ".join(str(item).rstrip(".") for item in causes) + ".")
    if recommendations:
        second_bits.append("For now, the most useful next step is " + str(recommendations[0]).rstrip(".") + ".")
    elif monitor:
        second_bits.append("I would keep an eye on " + str(monitor[0]).rstrip(".") + ".")

    if workflow in {"report_summary", "ocr_medical_report", "ai_insights"} and monitor:
        second_bits.append("The trend to keep watching is " + str(monitor[0]).rstrip(".") + ".")

    paragraphs = [first_paragraph]
    if second_bits:
        paragraphs.append(" ".join(_dedupe_sentences(second_bits)[:3]))

    if follow_up:
        paragraphs.append("The next question that would sharpen this is: " + str(follow_up[0]).rstrip(".?") + "?")
    if safety and _safe_text(payload.get("risk_level")).lower() in {"high", "emergency"}:
        paragraphs.append(_clean_sentence(str(safety[0])))
    return "\n\n".join(part for part in paragraphs if part).strip()


def humanize_response_payload(
    *,
    workflow: str,
    payload: dict[str, Any] | None,
    persona: dict[str, Any] | None = None,
    emotional_context: dict[str, Any] | None = None,
    continuity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    enriched = dict(payload or {})
    persona = persona if isinstance(persona, dict) else {}
    emotional_context = emotional_context if isinstance(emotional_context, dict) else {}
    continuity = continuity if isinstance(continuity, dict) else {}

    for key in ("summary", "clinical_summary", "clinical_interpretation", "clinical_insight", "message"):
        text = _safe_text(enriched.get(key))
        if not text:
            continue
        for source, target in REPETITIVE_PHRASES:
            text = re.sub(source, target, text, flags=re.IGNORECASE)
        text = re.sub(r"\bRetrieved medical knowledge\b", "Medical context", text, flags=re.IGNORECASE)
        text = re.sub(r"\bBased on your recent data\b", "From the overall pattern", text, flags=re.IGNORECASE)
        enriched[key] = _clean_sentence(text)

    message = _safe_text(enriched.get("message"))
    if not message or len(message.split()) < 15 or "based on your data" in message.lower():
        enriched["message"] = _build_message(
            workflow=workflow,
            payload=enriched,
            persona=persona,
            emotional_context=emotional_context,
            continuity=continuity,
        )

    enriched["persona"] = persona
    enriched["emotional_context"] = emotional_context
    enriched["continuity"] = continuity
    enriched["conversation_style"] = {
        "workflow": workflow,
        "pacing": _safe_text(_safe_dict(emotional_context.get("adaptation")).get("pacing"), "steady"),
        "tone": _safe_text(_safe_dict(emotional_context.get("adaptation")).get("tone"), "calm"),
        "paragraph_style": _safe_text(_safe_dict(persona.get("formatting_preferences")).get("paragraph_style")),
    }
    return enriched
