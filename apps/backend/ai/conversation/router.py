from __future__ import annotations

import re
from typing import Any, Awaitable, Callable

from .depth_controller import resolve_depth
from .escalation import detect_escalation
from .guardrails import apply_guardrails
from .intent import classify_intent


MessageHandler = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


BASE_SYSTEM_PROMPT = """
You are Arya, ArogyaAI's health assistant. You communicate like a warm,
experienced family doctor - not a textbook.

Your core principles:

1. LISTEN BEFORE YOU DIAGNOSE.
   Never jump to analysis without understanding the situation.
   Ask one clear question at a time, not five at once.

2. MATCH THE ENERGY OF THE MESSAGE.
   "hi" -> short friendly greeting.
   "thanks" -> brief warm acknowledgement.
   "my chest hurts" -> empathetic concern + ONE clarifying question.
   "analyze this report" -> thorough clinical interpretation.

3. NEVER OVER-EXPLAIN.
   Do not mention RAG sources unless the user asks.
   Do not repeat vitals, blood pressure context, or risk scores unless
   they are directly relevant to what was just asked.
   Do not add disclaimers to every message.

4. ASK ONE QUESTION, NOT FIVE.
   If you need more information, ask the single most important question.
   Wait for the answer before asking anything else.

5. ESCALATE NATURALLY.
   Conversation depth should grow only as the clinical situation warrants it.
   Start with curiosity. Build toward analysis.

6. SOUND HUMAN.
   Avoid: "Based on your recent health data...", "I've analyzed your vitals..."
   Prefer: "That's worth paying attention to.", "Tell me more about that."
   Use natural phrasing. Short sentences. Occasional warmth.

7. EMERGENCY EXCEPTION.
   If the user describes chest pain + breathlessness, or stroke symptoms,
   or anything life-threatening: skip all conversational pacing.
   Respond immediately: "This sounds serious. Please call emergency services now."
   Then add one brief, actionable sentence.
""".strip()

MODE_BLOCKS = {
    "micro": """
[micro mode]
Respond in 1-2 sentences only. No medical content. No analysis.
Do not ask more than one optional, light question.
""".strip(),
    "short": """
[short mode]
2-4 sentences. One clarifying question if needed.
No RAG. No risk analysis. No recommendation synthesis.
""".strip(),
    "medium": """
[medium mode]
Ask one empathetic clarifying question first.
Then offer a short, grounded response based on what the user shared.
Do not launch full analysis before understanding the situation.
Use RAG only if directly relevant. Cite sparingly.
""".strip(),
    "detailed": """
[detailed mode]
Structured but conversational. Use short paragraphs.
Explain your reasoning briefly. Cite key data points.
End with a clear, actionable suggestion.
No giant walls of text. Use whitespace.
""".strip(),
    "expert": """
[expert mode]
Full clinical interpretation mode.
Use structured output: summary -> findings -> implications -> recommendations.
Include relevant citations only where clinically meaningful.
Do not dump the entire analysis in the chat bubble.
""".strip(),
}

QUICK_REPLIES = ["Check symptoms", "View my risk score", "Upload a report"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", _clean_text(text).lower())


def _split_sentences(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", _clean_text(text)) if item.strip()]


def _truncate_sentences(text: str, limit: int = 3) -> str:
    sentences = _split_sentences(text)
    return " ".join(sentences[:limit]).strip()


def _deterministic_social_response(intent: str) -> str:
    if intent == "greeting":
        return "Hey! What would you like help with today?"
    if intent == "acknowledgement":
        return "Got it. Anything else on your mind?"
    if intent == "gratitude":
        return "Happy to help! Let me know if anything else comes up."
    if intent == "farewell":
        return "Take care. Reach out anytime."
    return "I'm here. What would you like help with?"


def _detect_primary_symptom(query: str) -> str:
    lowered = _normalize(query)
    if "chest" in lowered:
        return "chest pain"
    if "headache" in lowered or "head" in lowered:
        return "headache"
    if "breathe" in lowered or "breath" in lowered:
        return "shortness of breath"
    if "stomach" in lowered or "abdomen" in lowered:
        return "abdominal pain"
    if "dizzy" in lowered:
        return "dizziness"
    if "palpitation" in lowered or "heart rate" in lowered:
        return "palpitations"
    return "symptoms"


def _single_best_question(query: str) -> str:
    symptom = _detect_primary_symptom(query)
    if symptom == "chest pain":
        return "Where exactly do you feel it, and how long has it been going on?"
    if symptom == "headache":
        return "How long has this been happening, and do you notice it most after waking up or later in the day?"
    if symptom == "shortness of breath":
        return "Is it happening at rest, or mainly when you're moving around?"
    if symptom == "abdominal pain":
        return "Where in your abdomen do you feel it most, and when did it start?"
    if symptom == "dizziness":
        return "Did it start suddenly, and does it happen when you stand up or even at rest?"
    if symptom == "palpitations":
        return "Does it come in brief bursts, or is it staying elevated for a while?"
    return "Can you tell me when this started and what feels most noticeable right now?"


def _is_first_symptom_mention(
    user_context: dict[str, Any] | None,
    conversation_history: list[dict[str, Any]] | None,
) -> bool:
    context = user_context if isinstance(user_context, dict) else {}
    if isinstance(context.get("recent_symptoms"), list) and context.get("recent_symptoms"):
        return False
    if isinstance(context.get("symptoms_history"), list) and context.get("symptoms_history"):
        return False
    for item in (conversation_history or [])[-4:]:
        if not isinstance(item, dict) or _normalize(item.get("role")) != "user":
            continue
        prior = _normalize(item.get("content"))
        if any(token in prior for token in ("pain", "hurts", "dizzy", "breath", "report", "risk score")):
            return False
    return True


def _build_prompt(user_message: str, intent: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            BASE_SYSTEM_PROMPT,
            MODE_BLOCKS.get(str(intent.get("depth") or "short"), MODE_BLOCKS["short"]),
            f"User message: {user_message}",
            f"Intent: {intent.get('intent')}",
            f"Word limit: {intent.get('max_words')}",
            "Return valid JSON with keys: message, summary, follow_up_questions.",
        ]
    )


async def _direct_response(
    user_message: str,
    intent: dict[str, Any],
    *,
    llm_handler: MessageHandler | None,
) -> dict[str, Any]:
    if intent["intent"] in {"greeting", "acknowledgement", "gratitude", "farewell"}:
        return {"message": _deterministic_social_response(intent["intent"])}

    if intent["intent"] == "navigation_help":
        return {"message": "I can help with that. If you're trying to upload a report, open Reports and choose Upload a report."}
    if intent["intent"] == "onboarding_help":
        return {"message": "We can start wherever feels easiest. You can ask about symptoms, view your risk score, or upload a report."}
    if intent["intent"] == "clarification":
        return {"message": "I can break it down more simply. Which part felt unclear?"}
    if intent["intent"] == "casual_chat":
        return {"message": "I can help with symptoms, reports, and risk explanations. What would you like to dig into?"}

    if llm_handler is None:
        return {"message": "Tell me a little more, and I'll keep it simple."}
    payload = await llm_handler(_build_prompt(user_message, intent), intent)
    return payload if isinstance(payload, dict) else {"message": "Tell me a little more, and I'll keep it simple."}


def _build_emergency_payload() -> dict[str, Any]:
    return {
        "message": "This sounds serious. Please call emergency services now. If you can, do not drive yourself and get someone nearby to stay with you.",
        "summary": "Urgent safety escalation triggered.",
        "follow_up_questions": [],
        "quick_replies": [],
    }


def _build_clarifying_payload(user_message: str) -> dict[str, Any]:
    symptom = _detect_primary_symptom(user_message)
    openings = {
        "chest pain": "That's worth paying attention to.",
        "headache": "That sounds uncomfortable.",
        "shortness of breath": "That's important to take seriously.",
        "abdominal pain": "That's worth looking into.",
        "dizziness": "That can be unsettling.",
        "palpitations": "That's worth paying attention to.",
        "symptoms": "Thanks for telling me that.",
    }
    question = _single_best_question(user_message)
    return {
        "message": f"{openings.get(symptom, openings['symptoms'])} {question}",
        "summary": f"Initial clarification for {symptom}.",
        "follow_up_questions": [question],
    }


def _build_expert_sections(payload: dict[str, Any]) -> list[dict[str, str]]:
    summary = _clean_text(payload.get("summary") or payload.get("clinical_summary") or payload.get("message"))
    findings = ", ".join(str(item).strip() for item in (payload.get("possible_causes") or payload.get("contributing_factors") or [])[:4] if str(item).strip())
    implications = _clean_text(payload.get("clinical_interpretation") or payload.get("clinical_insight"))
    recommendations = "\n".join(
        f"- {str(item).strip()}"
        for item in (payload.get("recommendations") or [])[:4]
        if str(item).strip()
    )
    sections = [
        {"title": "Summary", "content": summary},
        {"title": "Findings", "content": findings},
        {"title": "Implications", "content": implications},
        {"title": "Recommendations", "content": recommendations},
    ]
    return [section for section in sections if _clean_text(section["content"])]


async def route_message(
    user_message: str,
    conversation_history: list[dict[str, Any]] | None,
    user_context: dict[str, Any] | None,
    *,
    lightweight_llm_call: MessageHandler | None = None,
    medical_llm_call: MessageHandler | None = None,
    expert_llm_call: MessageHandler | None = None,
    guardrails_enabled: bool = True,
    developer_flags: dict[str, Any] | None = None,
    llm_intent_fallback: Callable[[str, list[dict[str, Any]], dict[str, Any]], Awaitable[dict[str, Any] | None]] | None = None,
) -> dict[str, Any]:
    classified = await classify_intent(
        user_message,
        conversation_history=conversation_history,
        user_context=user_context,
        llm_fallback=llm_intent_fallback,
    )
    routed = resolve_depth(classified)
    escalation = detect_escalation(user_message, conversation_history, routed["mode"])
    if escalation["severity"] == "emergency":
        emergency_intent = {**routed, "intent": "emergency_concern", "mode": "medical", "depth": "short"}
        payload = _build_emergency_payload()
        payload["message"] = await apply_guardrails(
            payload["message"],
            emergency_intent,
            conversation_history,
            bypass=not guardrails_enabled or bool((developer_flags or {}).get("bypass_guardrails")),
        )
        return {**payload, **emergency_intent, "escalation": escalation, "quick_replies": []}

    if escalation["escalated"] and routed["mode"] == "casual":
        routed["mode"] = "medical"

    if routed["mode"] == "casual":
        payload = await _direct_response(user_message, routed, llm_handler=lightweight_llm_call)
        payload.setdefault("quick_replies", list(QUICK_REPLIES))
    elif routed["mode"] == "medical" and routed["intent"] == "symptom_report" and _is_first_symptom_mention(user_context, conversation_history):
        payload = _build_clarifying_payload(user_message)
    elif routed["mode"] == "medical":
        if medical_llm_call is None:
            payload = _build_clarifying_payload(user_message)
        else:
            payload = await medical_llm_call(user_message, routed)
    else:
        if expert_llm_call is None:
            payload = {"message": "I can analyze that in detail. Please share the report or the exact result you want me to interpret."}
        else:
            payload = await expert_llm_call(user_message, routed)

    payload = payload if isinstance(payload, dict) else {"message": _clean_text(payload)}
    payload.setdefault("summary", _truncate_sentences(payload.get("message") or "", 2))
    guarded_message = await apply_guardrails(
        payload.get("message") or payload.get("summary") or "",
        routed,
        conversation_history,
        bypass=not guardrails_enabled or bool((developer_flags or {}).get("bypass_guardrails")),
    )
    payload["message"] = guarded_message

    if routed["mode"] == "expert":
        full_analysis = _clean_text(payload.get("full_analysis") or payload.get("message"))
        payload["full_analysis"] = full_analysis
        payload["expert_sections"] = payload.get("expert_sections") if isinstance(payload.get("expert_sections"), list) else _build_expert_sections(payload)
        payload["summary_preview"] = _truncate_sentences(
            payload.get("summary_preview") or payload.get("summary") or payload.get("message"),
            3,
        )
        payload["message"] = payload["summary_preview"]

    return {
        **payload,
        **routed,
        "escalation": escalation,
    }
