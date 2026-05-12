from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .memory_snapshot import MemorySnapshot


class DialogueContext(BaseModel):
    workflow: str = "chatbot"
    user_id: str = ""
    session_id: str = "chat"
    query: str = ""
    intent: str = "conversation"
    mode: str = "casual"
    depth: str = "short"
    risk_level: str = "low"
    confidence_score: float | None = None
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    user_context: dict[str, Any] = Field(default_factory=dict)
    response_payload: dict[str, Any] = Field(default_factory=dict)
    emotional_context: dict[str, Any] = Field(default_factory=dict)
    persona: dict[str, Any] = Field(default_factory=dict)
    continuity: dict[str, Any] = Field(default_factory=dict)
    ml_data: dict[str, Any] = Field(default_factory=dict)
    rag_context: dict[str, Any] = Field(default_factory=dict)
    memory_snapshot: MemorySnapshot = Field(default_factory=MemorySnapshot)

    def compact_history(self, *, limit: int = 6) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        for item in self.conversation_history[-limit:]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip().lower()
            content = str(item.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            normalized.append({"role": role, "content": content[:240]})
        return normalized

    def word_count(self) -> int:
        return len([part for part in self.query.split() if part.strip()])
