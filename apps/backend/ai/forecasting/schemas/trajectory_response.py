from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PreventiveAlertResponse(BaseModel):
    severity: str
    title: str
    summary: str
    window: str
    domain: str
    recommendation: str
    escalation_level: str = "none"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrajectoryResponse(BaseModel):
    name: str
    window: str
    direction: str
    severity: str
    summary: str
    projected_change: float = 0.0
    confidence: float = 0.0
    uncertainty: float = 1.0
    projection_strength: float = 0.0
    signal_quality: float = 0.0
    stability: float = 0.0
    supporting_domains: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
