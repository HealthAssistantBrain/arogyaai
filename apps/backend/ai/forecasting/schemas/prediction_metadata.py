from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProjectionContributor(BaseModel):
    label: str
    value: float | str | None = None
    direction: str = "stable"
    impact: float = 0.0
    detail: str = ""


class ProjectionMetrics(BaseModel):
    confidence: float = 0.0
    uncertainty: float = 1.0
    projection_strength: float = 0.0
    signal_quality: float = 0.0
    stability: float = 0.0
    volatility: float = 0.0


class PredictionMetadata(BaseModel):
    baseline_value: float | None = None
    current_value: float | None = None
    projected_value: float | None = None
    current_score: float | None = None
    projected_score: float | None = None
    current_risk: float | None = None
    projected_risk: float | None = None
    direction: str = "stable"
    horizon_days: int = 1
    data_points: int = 0
    source_count: int = 0
    evidence: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    extras: dict[str, Any] = Field(default_factory=dict)
