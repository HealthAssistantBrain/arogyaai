from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StructuredSection(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    title: str
    content: str = ""
    bullets: list[str] = Field(default_factory=list)
    priority: int = 0
    confidence_hint: float | None = None


class RenderCard(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    title: str
    body: str = ""
    items: list[str] = Field(default_factory=list)
    tone: str = "neutral"


class RenderAlert(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    level: str
    title: str
    message: str


class ConfidenceBadge(BaseModel):
    model_config = ConfigDict(extra="allow")

    label: str
    score: float
    tone: str
    reasoning: str


class FrontendRenderContract(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: str = "v1"
    display_mode: str = "clinical_brief"
    sections: list[StructuredSection] = Field(default_factory=list)
    cards: list[RenderCard] = Field(default_factory=list)
    alerts: list[RenderAlert] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)
    charts: list[dict[str, Any]] = Field(default_factory=list)
    confidence_badge: ConfidenceBadge | None = None


class StreamingContract(BaseModel):
    model_config = ConfigDict(extra="allow")

    supported: bool = True
    progressive_hydration: bool = True
    partial_safe_fields: list[str] = Field(default_factory=list)
    section_order: list[str] = Field(default_factory=list)
    hydrated_sections: list[str] = Field(default_factory=list)


class FormatterDiagnostics(BaseModel):
    model_config = ConfigDict(extra="allow")

    formatter_version: str = "2026.05"
    normalized_provider: str = "default"
    repairs_applied: list[str] = Field(default_factory=list)
    validation_flags: list[str] = Field(default_factory=list)
    confidence_breakdown: dict[str, float] = Field(default_factory=dict)
    malformed_input_detected: bool = False
    raw_contract_preserved: bool = True


class StructuredMedicalResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str = "success"
    workflow: str
    provider: str = ""
    model: str = ""
    timestamp: str
    response_id: str
    summary: str = ""
    structured_sections: list[StructuredSection] = Field(default_factory=list)
    insights: list[Any] = Field(default_factory=list)
    recommendations: list[Any] = Field(default_factory=list)
    risk_factors: list[Any] = Field(default_factory=list)
    confidence_score: float = 0.0
    confidence_label: str = "Low"
    confidence_reasoning: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    rag_sources: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[Any] = Field(default_factory=list)
    medical_disclaimer: str = ""
    latency_ms: float = 0.0
    token_usage: dict[str, Any] = Field(default_factory=dict)
    cache_hit: bool = False
    raw_response: str = ""
    rendering: FrontendRenderContract | None = None
    streaming: StreamingContract | None = None
    formatter_diagnostics: FormatterDiagnostics | None = None
