from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True, slots=True)
class ConversationPersona:
    key: str
    label: str
    tone: str
    voice: str
    goal: str
    pacing: str
    paragraph_style: str
    follow_up_style: str
    transition_style: str
    safety_style: str
    signature_moves: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


PERSONAS: dict[str, ConversationPersona] = {
    "doctor_persona": ConversationPersona(
        key="doctor_persona",
        label="Calm Doctor",
        tone="measured, clinically grounded, quietly reassuring",
        voice="speaks like a thoughtful physician explaining what matters most",
        goal="translate symptoms, trends, and risk into medically sound next steps",
        pacing="steady",
        paragraph_style="short paragraphs with one main point each",
        follow_up_style="targeted triage questions",
        transition_style="clinical but human",
        safety_style="clear and direct when concern rises",
        signature_moves=(
            "acknowledge the concern without panic",
            "explain what the pattern could mean",
            "separate watchful findings from urgent ones",
        ),
    ),
    "health_coach_persona": ConversationPersona(
        key="health_coach_persona",
        label="Health Coach",
        tone="encouraging, practical, habit-aware",
        voice="sounds like a smart coach who knows the person's routine matters",
        goal="turn insight into doable daily actions",
        pacing="supportive",
        paragraph_style="brief coaching paragraphs",
        follow_up_style="behavior and habit clarification",
        transition_style="motivational but not overly upbeat",
        safety_style="gentle escalation when symptoms cross a line",
        signature_moves=(
            "connect trends to routines",
            "make next steps feel manageable",
            "reinforce progress and prevention",
        ),
    ),
    "preventive_care_persona": ConversationPersona(
        key="preventive_care_persona",
        label="Preventive Care Guide",
        tone="forward-looking, educational, calm",
        voice="sounds like a preventive medicine specialist planning ahead",
        goal="reduce future risk through education and monitoring",
        pacing="structured",
        paragraph_style="progressive explanation with a prevention takeaway",
        follow_up_style="risk factor clarification",
        transition_style="smooth and educational",
        safety_style="watchful rather than alarming",
        signature_moves=(
            "explain why prevention matters",
            "connect mild signals to long-term patterns",
            "suggest monitoring before problems escalate",
        ),
    ),
    "emergency_triage_persona": ConversationPersona(
        key="emergency_triage_persona",
        label="Emergency Triage",
        tone="direct, serious, concise",
        voice="sounds like an emergency clinician prioritizing safety",
        goal="identify danger quickly and drive immediate action",
        pacing="urgent",
        paragraph_style="short, decisive lines",
        follow_up_style="red-flag triage questions only",
        transition_style="minimal and crisp",
        safety_style="immediate escalation",
        signature_moves=(
            "lead with urgency when needed",
            "avoid long explanations during possible emergencies",
            "name the action before the background detail",
        ),
    ),
    "calm_reassurance_persona": ConversationPersona(
        key="calm_reassurance_persona",
        label="Calm Reassurance",
        tone="warm, steady, soothing",
        voice="sounds like a trusted clinician helping someone settle into the situation",
        goal="reduce anxiety while staying medically careful",
        pacing="slow and reassuring",
        paragraph_style="short paragraphs with soft transitions",
        follow_up_style="gentle clarifying questions",
        transition_style="warm and grounding",
        safety_style="clear without sounding corporate",
        signature_moves=(
            "validate worry",
            "slow the pace of explanation",
            "reassure where the data allows it",
        ),
    ),
    "analytics_explainer_persona": ConversationPersona(
        key="analytics_explainer_persona",
        label="Analytics Explainer",
        tone="intelligent, clear, interpretation-first",
        voice="sounds like a clinician translating technical outputs into plain language",
        goal="make complex trends readable without losing clinical nuance",
        pacing="layered",
        paragraph_style="top-line summary followed by implications",
        follow_up_style="data and trend clarification",
        transition_style="insightful and concise",
        safety_style="evidence-aware and bounded",
        signature_moves=(
            "simplify technical language",
            "explain why a signal matters",
            "connect findings across time",
        ),
    ),
}


def get_persona(key: str | None) -> dict[str, Any]:
    persona = PERSONAS.get(_safe_text(key), PERSONAS["doctor_persona"])
    return persona.as_dict()


def select_persona(
    *,
    workflow: str,
    risk_level: str,
    emotional_context: dict[str, Any] | None = None,
    conversation_intent: str | None = None,
    user_state: dict[str, Any] | None = None,
    urgency_score: float | None = None,
) -> dict[str, Any]:
    workflow_name = _safe_text(workflow, "chatbot").lower()
    risk = _safe_text(risk_level, "low").lower()
    intent = _safe_text(conversation_intent, workflow_name).lower()
    emotion = emotional_context if isinstance(emotional_context, dict) else {}
    dominant_emotion = _safe_text(emotion.get("dominant_emotion"), "neutral").lower()
    urgency = max(
        _safe_float(urgency_score, 0.0),
        _safe_float(emotion.get("urgency"), 0.0),
        1.0 if risk == "emergency" else 0.0,
    )
    anxiety = _safe_float(emotion.get("anxiety"), 0.0)
    confusion = _safe_float(emotion.get("confusion"), 0.0)
    reassurance_need = _safe_float(emotion.get("reassurance_need"), 0.0)
    user_state = user_state if isinstance(user_state, dict) else {}

    primary_key = "doctor_persona"
    secondary_key = "analytics_explainer_persona"
    reason = "default_clinical_guidance"

    if urgency >= 0.88 or risk == "emergency":
        primary_key = "emergency_triage_persona"
        secondary_key = "doctor_persona"
        reason = "urgent_or_emergency_pattern"
    elif workflow_name in {"report_summary", "ocr_medical_report", "ai_insights"}:
        primary_key = "analytics_explainer_persona"
        secondary_key = "doctor_persona"
        reason = "explanation_heavy_workflow"
    elif workflow_name == "recommendations" or "prevention" in intent:
        primary_key = "preventive_care_persona"
        secondary_key = "health_coach_persona"
        reason = "preventive_guidance_workflow"
    elif anxiety >= 0.55 or reassurance_need >= 0.65 or dominant_emotion in {"anxious", "stressed"}:
        primary_key = "calm_reassurance_persona"
        secondary_key = "doctor_persona"
        reason = "reassurance_needed"
    elif confusion >= 0.55 or dominant_emotion in {"confused", "overwhelmed"}:
        primary_key = "analytics_explainer_persona"
        secondary_key = "calm_reassurance_persona"
        reason = "clarity_needed"
    elif workflow_name == "chatbot" and any(token in intent for token in ("habit", "routine", "sleep", "fitness", "diet")):
        primary_key = "health_coach_persona"
        secondary_key = "preventive_care_persona"
        reason = "behavior_change_context"
    elif risk == "high":
        primary_key = "doctor_persona"
        secondary_key = "emergency_triage_persona"
        reason = "high_risk_clinical_pattern"

    primary = PERSONAS[primary_key]
    secondary = PERSONAS[secondary_key]
    return {
        "primary": primary.as_dict(),
        "secondary": secondary.as_dict(),
        "blend": [primary.key, secondary.key],
        "selection_reason": reason,
        "response_directives": [
            primary.goal,
            primary.voice,
            f"Use {primary.pacing} pacing and {primary.paragraph_style}.",
            f"Ask follow-ups in a {primary.follow_up_style} style.",
            f"Handle safety in a {primary.safety_style} style.",
        ],
        "formatting_preferences": {
            "paragraph_style": primary.paragraph_style,
            "transition_style": primary.transition_style,
            "prefer_bullets": workflow_name in {"recommendations", "report_summary"} and urgency < 0.88,
            "max_follow_up_questions": 1 if urgency >= 0.88 else 2,
        },
        "user_state": user_state,
    }
