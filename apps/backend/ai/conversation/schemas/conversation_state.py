from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConversationState(BaseModel):
    session_id: str = "chat"
    mode: str = "casual"
    depth: str = "short"
    active_topics: list[str] = Field(default_factory=list)
    continuity_summary: str = ""
    follow_up_pending: bool = False
    follow_up_focus: list[str] = Field(default_factory=list)
    recent_recommendations: list[str] = Field(default_factory=list)
    response_chunks: int = 0
    typing_label: str = "Arya is typing..."
    chunk_strategy: str = "sentence"
    pacing: dict[str, Any] = Field(default_factory=dict)
    compression: dict[str, Any] = Field(default_factory=dict)

    def to_api_payload(self) -> dict[str, Any]:
        return self.model_dump()
