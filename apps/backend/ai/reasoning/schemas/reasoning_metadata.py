from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReasoningMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    reasoning_version: str = "cognitive-v1"
    generated_at: str = ""
    source: str = "deterministic_reasoning"
    workflow: str = "ai_insights"
    evidence_count: int = 0
    observed_windows: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    safety_pipeline: list[str] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
