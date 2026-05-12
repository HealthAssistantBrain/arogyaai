from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .cognitive_summary import CognitiveSummary
from .reasoning_metadata import ReasoningMetadata


class ReasoningCard(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: str = "signal"
    domain: str = "general"
    title: str
    summary: str
    severity: str = "low"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    timeframe: str = "7d"
    evidence: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RecommendationItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    why: str
    priority: str = "medium"
    timeframe: str = "next few days"
    evidence: list[str] = Field(default_factory=list)
    type: str = "preventive"


class ConfidenceIndicator(BaseModel):
    model_config = ConfigDict(extra="allow")

    label: str
    value: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str = ""


class ReasoningResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    summary: str = ""
    clinical_narrative: str = ""
    health_story: dict[str, Any] = Field(default_factory=dict)
    trajectory_explanation: dict[str, Any] = Field(default_factory=dict)
    cognitive_summary: CognitiveSummary = Field(default_factory=CognitiveSummary)
    reasoning_cards: list[ReasoningCard] = Field(default_factory=list)
    causal_explanations: list[ReasoningCard] = Field(default_factory=list)
    trend_explanations: list[ReasoningCard] = Field(default_factory=list)
    deterioration_reasoning: dict[str, Any] = Field(default_factory=dict)
    recovery_projection: dict[str, Any] = Field(default_factory=dict)
    preventive_reasoning: dict[str, Any] = Field(default_factory=dict)
    disease_simulation_reasoning: dict[str, Any] = Field(default_factory=dict)
    follow_up_questions: list[str] = Field(default_factory=list)
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    confidence_indicators: list[ConfidenceIndicator] = Field(default_factory=list)
    memory_snapshot: dict[str, Any] = Field(default_factory=dict)
    memory_persistence: dict[str, Any] = Field(default_factory=dict)
    safety: dict[str, Any] = Field(default_factory=dict)
    metadata: ReasoningMetadata = Field(default_factory=ReasoningMetadata)
