from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..utils import utc_now


class InterventionAction(BaseModel):
    action_id: str
    title: str
    detail: str
    priority: str = "medium"
    domains: list[str] = Field(default_factory=list)
    timing: str = "today"
    expected_impact: float = 0.0
    adherence_probability: float = 0.0
    rationale: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    source_signal_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InterventionPlan(BaseModel):
    plan_id: str
    headline: str
    summary: str
    escalation_level: str = "monitor"
    priorities: list[InterventionAction] = Field(default_factory=list)
    monitoring_focus: list[str] = Field(default_factory=list)
    follow_up_window_hours: int = 24
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)
