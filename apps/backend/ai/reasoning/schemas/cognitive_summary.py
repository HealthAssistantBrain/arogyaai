from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CognitiveSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    headline: str = ""
    short_summary: str = ""
    trend_state: str = "stable"
    care_priority: str = "low"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    dominant_theme: str = ""
    baseline_awareness: str = ""
    next_best_action: str = ""
    conversational_continuity: str = ""
