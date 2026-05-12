from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from ..compression import DialoguePruning
from ..memory import ConversationalMemory
from ..schemas import ConversationState, DialogueContext
from .context_router import ContextRouter
from .dialogue_orchestrator import DialogueOrchestrator
from .response_planner import ResponsePlanner

logger = logging.getLogger("uvicorn.error")


class ConversationEngine:
    def __init__(self) -> None:
        self.memory = ConversationalMemory()
        self.router = ContextRouter()
        self.planner = ResponsePlanner()
        self.dialogue = DialogueOrchestrator()
        self.pruning = DialoguePruning()

    def enrich(
        self,
        *,
        workflow: str,
        payload: dict[str, Any],
        query: str,
        user_context: dict[str, Any] | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        emotional_context: dict[str, Any] | None = None,
        persona: dict[str, Any] | None = None,
        continuity: dict[str, Any] | None = None,
        risk_level: str = "",
        conversation_intent: str = "",
        session_id: str = "chat",
        user_id: str = "",
        ml_data: dict[str, Any] | None = None,
        rag_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        dialogue_context = DialogueContext(
            workflow=workflow,
            user_id=user_id,
            session_id=session_id or "chat",
            query=query,
            intent=conversation_intent or workflow or "conversation",
            mode=str(payload.get("mode") or "casual"),
            depth=str(payload.get("depth") or "short"),
            risk_level=risk_level or str(payload.get("risk_level") or "low"),
            confidence_score=self._coerce_float(payload.get("confidence_score")),
            conversation_history=self.pruning.prune_history(conversation_history, limit=8),
            user_context=dict(user_context or {}),
            response_payload=dict(payload or {}),
            emotional_context=dict(emotional_context or {}),
            persona=dict(persona or {}),
            continuity=dict(continuity or {}),
            ml_data=dict(ml_data or {}),
            rag_context=dict(rag_context or {}),
        )
        snapshot = self.memory.build_snapshot(dialogue_context)
        dialogue_context.memory_snapshot = snapshot
        routing = self.router.route(dialogue_context, snapshot)
        plan = self.planner.plan(dialogue_context, snapshot, routing)
        state = self.memory.to_state(dialogue_context, snapshot)
        state.mode = dialogue_context.mode
        state.depth = dialogue_context.depth
        result = self.dialogue.orchestrate(
            context=dialogue_context,
            snapshot=snapshot,
            plan=plan,
            state=state,
        )
        logger.info(
            "[TOPIC_CONTINUITY] session=%s topics=%s",
            dialogue_context.session_id,
            ",".join(snapshot.topic.active_topics[:4]),
        )
        logger.info(
            "[RESPONSE_COMPRESSED] session=%s summary_len=%s",
            dialogue_context.session_id,
            len(snapshot.compressed_summary),
        )
        return {
            **payload,
            "message": result["message"],
            "follow_up_questions": result["follow_up_questions"],
            "quick_replies": result["quick_replies"],
            "streaming": result["streaming"],
            "conversation_state": result["conversation_state"],
            "memory_snapshot": snapshot.model_dump(),
            "context_compression": result["context_compression"],
            "physiological_grounding": result["physiological_grounding"],
            "tone_profile": result["tone_profile"],
            "calibration": result["calibration"],
        }

    def build_streaming_metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        streaming = payload.get("streaming") if isinstance(payload.get("streaming"), dict) else {}
        if streaming.get("chunks"):
            return streaming
        from ..dialogue import ConversationalPacing

        pacing = ConversationalPacing()
        return pacing.build(
            str(payload.get("message") or payload.get("summary") or ""),
            depth=str(payload.get("depth") or "short"),
            target_chunk_words=22,
        )

    async def stream_payload(self, payload: dict[str, Any]) -> AsyncIterator[str]:
        streaming = self.build_streaming_metadata(payload)
        session_id = str(
            (payload.get("conversation_state") or {}).get("session_id")
            or payload.get("session_id")
            or "chat"
        )
        yield self._event("meta", {"session_id": session_id, "streaming": streaming})
        yield self._event(
            "typing",
            {
                "label": streaming.get("typing_label") or "Arya is typing...",
                "depth": payload.get("depth") or "short",
            },
        )
        await asyncio.sleep(0)
        for index, chunk in enumerate(streaming.get("chunks") or []):
            yield self._event(
                "chunk",
                {
                    "index": index,
                    "content": chunk,
                    "done": False,
                },
            )
            await asyncio.sleep(float(streaming.get("typing_delay_ms") or 75) / 1000.0)
        yield self._event("final", {"payload": payload, "done": True})

    def _event(self, event_type: str, payload: dict[str, Any]) -> str:
        return json.dumps({"event": event_type, "data": payload}, default=str) + "\n"

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
