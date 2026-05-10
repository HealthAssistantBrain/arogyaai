from __future__ import annotations

from typing import Any

from .continuity import build_continuity_snapshot, build_memory_persistence
from .emotion import infer_emotional_context
from .followup_engine import generate_follow_up_questions
from .humanizer import humanize_response_payload
from .personas import select_persona


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


class ConversationIntelligenceService:
    def build_runtime_context(
        self,
        *,
        workflow: str,
        query: str = "",
        response_payload: dict[str, Any] | None = None,
        user_context: dict[str, Any] | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        risk_level: str = "",
        conversation_intent: str = "",
        urgency_score: float | None = None,
    ) -> dict[str, Any]:
        context = user_context if isinstance(user_context, dict) else {}
        payload = response_payload if isinstance(response_payload, dict) else {}
        conversation_state = _safe_dict(context.get("conversation_state"))
        emotional_context = infer_emotional_context(
            query=query,
            conversation_history=conversation_history,
            conversation_state=conversation_state,
        )
        continuity = build_continuity_snapshot(
            user_context=context,
            conversation_history=conversation_history,
            response_payload=payload,
        )
        persona = select_persona(
            workflow=workflow,
            risk_level=risk_level or _safe_text(payload.get("risk_level"), "low"),
            emotional_context=emotional_context,
            conversation_intent=conversation_intent or workflow,
            user_state={
                "follow_up_pending": bool(conversation_state.get("follow_up_pending")),
                "recent_emotions": _safe_list(conversation_state.get("recent_emotions")),
            },
            urgency_score=urgency_score,
        )
        follow_up_questions = generate_follow_up_questions(
            query=query,
            symptoms=payload.get("symptoms") or context.get("recent_symptoms") or context.get("symptoms_history"),
            risk_level=risk_level or _safe_text(payload.get("risk_level"), "low"),
            emotional_context=emotional_context,
            conversation_history=conversation_history,
            user_context=context,
            workflow=workflow,
            limit=int(_safe_dict(persona.get("formatting_preferences")).get("max_follow_up_questions") or 2),
        )
        return {
            "emotion": emotional_context,
            "continuity": continuity,
            "persona": persona,
            "follow_up_questions": follow_up_questions,
        }

    def enrich_response(
        self,
        *,
        workflow: str,
        response_payload: dict[str, Any] | None,
        query: str = "",
        user_context: dict[str, Any] | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        risk_level: str = "",
        conversation_intent: str = "",
        urgency_score: float | None = None,
    ) -> dict[str, Any]:
        payload = dict(response_payload or {})
        runtime = self.build_runtime_context(
            workflow=workflow,
            query=query,
            response_payload=payload,
            user_context=user_context,
            conversation_history=conversation_history,
            risk_level=risk_level,
            conversation_intent=conversation_intent,
            urgency_score=urgency_score,
        )
        if not _safe_list(payload.get("follow_up_questions")):
            payload["follow_up_questions"] = runtime["follow_up_questions"]
        payload = humanize_response_payload(
            workflow=workflow,
            payload=payload,
            persona=runtime["persona"],
            emotional_context=runtime["emotion"],
            continuity=runtime["continuity"],
        )
        payload["memory_persistence"] = build_memory_persistence(
            response_payload=payload,
            emotional_context=runtime["emotion"],
            persona=runtime["persona"],
            continuity=runtime["continuity"],
        )
        return payload

    def prompt_context(
        self,
        *,
        workflow: str,
        query: str = "",
        user_context: dict[str, Any] | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        response_payload: dict[str, Any] | None = None,
        risk_level: str = "",
        conversation_intent: str = "",
    ) -> dict[str, Any]:
        runtime = self.build_runtime_context(
            workflow=workflow,
            query=query,
            response_payload=response_payload,
            user_context=user_context,
            conversation_history=conversation_history,
            risk_level=risk_level,
            conversation_intent=conversation_intent,
        )
        return {
            "persona": runtime["persona"],
            "emotional_context": runtime["emotion"],
            "continuity": runtime["continuity"],
            "suggested_follow_up_questions": runtime["follow_up_questions"],
        }
