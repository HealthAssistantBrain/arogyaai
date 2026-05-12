from __future__ import annotations

import logging
from typing import Any

from .core import ConversationEngine
from .continuity import build_continuity_snapshot, build_memory_persistence
from .emotion import infer_emotional_context, neutral_emotional_context
from .followup_engine import generate_follow_up_questions
from .humanizer import humanize_response_payload
from .personas import select_persona
from .schemas import DialogueContext

logger = logging.getLogger("uvicorn.error")


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _fallback_continuity() -> dict[str, Any]:
    return build_continuity_snapshot(
        user_context={},
        conversation_history=[],
        response_payload={},
    )


def _fallback_persona(
    *,
    workflow: str,
    risk_level: str,
    emotional_context: dict[str, Any] | None = None,
    conversation_intent: str = "",
    conversation_state: dict[str, Any] | None = None,
    urgency_score: float | None = None,
) -> dict[str, Any]:
    try:
        return select_persona(
            workflow=workflow,
            risk_level=risk_level or "low",
            emotional_context=emotional_context or neutral_emotional_context(),
            conversation_intent=conversation_intent or workflow,
            user_state={
                "follow_up_pending": bool(_safe_dict(conversation_state).get("follow_up_pending")),
                "recent_emotions": _safe_list(_safe_dict(conversation_state).get("recent_emotions")),
            },
            urgency_score=urgency_score,
        )
    except Exception:
        return {
            "primary": {"key": "doctor_persona", "label": "Calm Doctor"},
            "secondary": {"key": "analytics_explainer_persona", "label": "Analytics Explainer"},
            "blend": ["doctor_persona", "analytics_explainer_persona"],
            "selection_reason": "runtime_fallback",
            "response_directives": [],
            "formatting_preferences": {
                "paragraph_style": "short paragraphs with one main point each",
                "transition_style": "clinical but human",
                "prefer_bullets": False,
                "max_follow_up_questions": 2,
            },
            "user_state": {},
        }


class ConversationIntelligenceService:
    def __init__(self) -> None:
        self.engine = ConversationEngine()

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
        session_id: str = "chat",
        user_id: str = "",
        ml_data: dict[str, Any] | None = None,
        rag_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = user_context if isinstance(user_context, dict) else {}
        payload = response_payload if isinstance(response_payload, dict) else {}
        conversation_state = _safe_dict(context.get("conversation_state"))
        resolved_risk_level = risk_level or _safe_text(payload.get("risk_level"), "low")

        emotional_context = neutral_emotional_context()
        try:
            emotional_context = infer_emotional_context(
                query=query,
                conversation_history=conversation_history,
                conversation_state=conversation_state,
            )
        except Exception as exc:
            logger.warning("Conversation emotion inference failed; using neutral fallback | workflow=%s error=%s", workflow, exc, exc_info=True)

        try:
            continuity = build_continuity_snapshot(
                user_context=context,
                conversation_history=conversation_history,
                response_payload=payload,
            )
        except Exception as exc:
            logger.warning("Conversation continuity build failed; using empty snapshot | workflow=%s error=%s", workflow, exc, exc_info=True)
            continuity = _fallback_continuity()

        try:
            persona = select_persona(
                workflow=workflow,
                risk_level=resolved_risk_level,
                emotional_context=emotional_context,
                conversation_intent=conversation_intent or workflow,
                user_state={
                    "follow_up_pending": bool(conversation_state.get("follow_up_pending")),
                    "recent_emotions": _safe_list(conversation_state.get("recent_emotions")),
                },
                urgency_score=urgency_score,
            )
        except Exception as exc:
            logger.warning("Conversation persona selection failed; using default persona | workflow=%s error=%s", workflow, exc, exc_info=True)
            persona = _fallback_persona(
                workflow=workflow,
                risk_level=resolved_risk_level,
                emotional_context=emotional_context,
                conversation_intent=conversation_intent,
                conversation_state=conversation_state,
                urgency_score=urgency_score,
            )

        try:
            follow_up_questions = generate_follow_up_questions(
                query=query,
                symptoms=payload.get("symptoms") or context.get("recent_symptoms") or context.get("symptoms_history"),
                risk_level=resolved_risk_level,
                emotional_context=emotional_context,
                conversation_history=conversation_history,
                user_context=context,
                workflow=workflow,
                limit=int(_safe_dict(persona.get("formatting_preferences")).get("max_follow_up_questions") or 2),
            )
        except Exception as exc:
            logger.warning("Conversation follow-up generation failed; continuing without follow-up questions | workflow=%s error=%s", workflow, exc, exc_info=True)
            follow_up_questions = []
        return {
            "emotion": emotional_context,
            "continuity": continuity,
            "persona": persona,
            "follow_up_questions": follow_up_questions,
            "session_id": session_id,
            "user_id": user_id,
            "ml_data": ml_data if isinstance(ml_data, dict) else {},
            "rag_context": rag_context if isinstance(rag_context, dict) else {},
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
        session_id: str = "chat",
        user_id: str = "",
        ml_data: dict[str, Any] | None = None,
        rag_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = dict(response_payload or {})
        context = user_context if isinstance(user_context, dict) else {}
        runtime = self.build_runtime_context(
            workflow=workflow,
            query=query,
            response_payload=payload,
            user_context=user_context,
            conversation_history=conversation_history,
            risk_level=risk_level,
            conversation_intent=conversation_intent,
            urgency_score=urgency_score,
            session_id=session_id,
            user_id=user_id,
            ml_data=ml_data,
            rag_context=rag_context,
        )
        if not _safe_list(payload.get("follow_up_questions")):
            payload["follow_up_questions"] = runtime["follow_up_questions"]
        try:
            payload = humanize_response_payload(
                workflow=workflow,
                payload=payload,
                persona=runtime["persona"],
                emotional_context=runtime["emotion"],
                continuity=runtime["continuity"],
            )
        except Exception as exc:
            logger.warning("Conversation response humanization failed; keeping original payload | workflow=%s error=%s", workflow, exc, exc_info=True)
            payload["persona"] = runtime["persona"]
            payload["emotional_context"] = runtime["emotion"]
            payload["continuity"] = runtime["continuity"]
        payload.setdefault(
            "mode",
            "expert"
            if workflow in {"report_summary", "ocr_medical_report"}
            else "medical"
            if workflow in {"chatbot", "recommendations", "symptom_analysis", "ai_insights"}
            else "casual",
        )
        payload.setdefault(
            "depth",
            "expert"
            if payload["mode"] == "expert"
            else "detailed"
            if payload["mode"] == "medical" and _safe_text(payload.get("risk_level")).lower() in {"medium", "high"}
            else "medium"
            if payload["mode"] == "medical"
            else "short",
        )
        try:
            payload["memory_persistence"] = build_memory_persistence(
                response_payload=payload,
                emotional_context=runtime["emotion"],
                persona=runtime["persona"],
                continuity=runtime["continuity"],
            )
        except Exception as exc:
            logger.warning("Conversation memory persistence snapshot failed; using safe fallback | workflow=%s error=%s", workflow, exc, exc_info=True)
            payload["memory_persistence"] = {
                "summary": _safe_text(payload.get("summary") or payload.get("message")),
                "risk_level": _safe_text(payload.get("risk_level")),
                "follow_up_questions": _safe_list(payload.get("follow_up_questions")),
                "recommendations": _safe_list(payload.get("recommendations")),
                "symptoms": _safe_list(payload.get("symptoms")),
                "dominant_emotion": _safe_text(runtime["emotion"].get("dominant_emotion"), "neutral"),
                "reassurance_level": _safe_text(_safe_dict(runtime["emotion"].get("adaptation")).get("reassurance_level"), "light"),
                "persona": _safe_text(_safe_dict(runtime["persona"].get("primary")).get("key"), "doctor_persona"),
                "continuity_reference": _safe_text(runtime["continuity"].get("reference")),
            }

        try:
            return self.engine.enrich(
                workflow=workflow,
                payload=payload,
                query=query,
                user_context=context,
                conversation_history=conversation_history,
                emotional_context=runtime["emotion"],
                persona=runtime["persona"],
                continuity=runtime["continuity"],
                risk_level=risk_level or _safe_text(payload.get("risk_level"), "low"),
                conversation_intent=conversation_intent or workflow,
                session_id=session_id,
                user_id=user_id,
                ml_data=runtime["ml_data"],
                rag_context=runtime["rag_context"],
            )
        except Exception as exc:
            logger.warning("Conversation engine enrichment failed; returning minimally enriched payload | workflow=%s error=%s", workflow, exc, exc_info=True)
            message = _safe_text(
                payload.get("message") or payload.get("summary") or payload.get("understanding"),
                "I'm here to help. Tell me a bit more about what feels most important right now.",
            )
            payload["message"] = message
            payload.setdefault("summary", message)
            payload.setdefault("follow_up_questions", runtime["follow_up_questions"])
            payload.setdefault("quick_replies", [])
            payload["persona"] = runtime["persona"]
            payload["emotional_context"] = runtime["emotion"]
            payload["continuity"] = runtime["continuity"]
            conversation_state = _safe_dict(payload.get("conversation_state"))
            conversation_state.setdefault("session_id", session_id or "chat")
            payload["conversation_state"] = conversation_state
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
        session_id: str = "chat",
        user_id: str = "",
        ml_data: dict[str, Any] | None = None,
        rag_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        runtime = self.build_runtime_context(
            workflow=workflow,
            query=query,
            response_payload=response_payload,
            user_context=user_context,
            conversation_history=conversation_history,
            risk_level=risk_level,
            conversation_intent=conversation_intent,
            session_id=session_id,
            user_id=user_id,
            ml_data=ml_data,
            rag_context=rag_context,
        )
        try:
            dialogue_context = DialogueContext(
                workflow=workflow,
                user_id=user_id,
                session_id=session_id,
                query=query,
                intent=conversation_intent or workflow,
                mode=str((response_payload or {}).get("mode") or "medical"),
                depth=str((response_payload or {}).get("depth") or "medium"),
                risk_level=risk_level or _safe_text((response_payload or {}).get("risk_level"), "low"),
                conversation_history=conversation_history or [],
                user_context=user_context or {},
                response_payload=response_payload or {},
                emotional_context=runtime["emotion"],
                persona=runtime["persona"],
                continuity=runtime["continuity"],
                ml_data=runtime["ml_data"],
                rag_context=runtime["rag_context"],
            )
            snapshot = self.engine.memory.build_snapshot(dialogue_context)
            return {
                "persona": runtime["persona"],
                "emotional_context": runtime["emotion"],
                "continuity": runtime["continuity"],
                "suggested_follow_up_questions": runtime["follow_up_questions"],
                "memory_snapshot": snapshot.to_prompt_payload(),
                "compressed_context": snapshot.compressed_summary,
                "active_topics": snapshot.topic.active_topics[:4],
            }
        except Exception as exc:
            logger.warning("Conversation prompt context build failed; returning safe prompt context fallback | workflow=%s error=%s", workflow, exc, exc_info=True)
            return {
                "persona": runtime["persona"],
                "emotional_context": runtime["emotion"],
                "continuity": runtime["continuity"],
                "suggested_follow_up_questions": runtime["follow_up_questions"],
                "memory_snapshot": {},
                "compressed_context": "",
                "active_topics": [],
            }
