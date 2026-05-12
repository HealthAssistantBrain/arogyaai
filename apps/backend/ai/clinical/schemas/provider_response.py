from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .medical_timeline import TimelineEvidence


class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    patient_id: str
    generated_at: str
    query: str
    intent: str
    answer: str
    reasoning: str
    confidence: float
    grounded_evidence: list[TimelineEvidence] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    cards: list[dict[str, object]] = Field(default_factory=list)
    escalation: dict[str, object] = Field(default_factory=dict)
    safety: dict[str, object] = Field(default_factory=dict)


class ProviderDashboardSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    generated_at: str
    total_patients: int
    highest_risk_users: list[dict[str, object]] = Field(default_factory=list)
    worsening_physiological_trends: list[dict[str, object]] = Field(default_factory=list)
    escalation_candidates: list[dict[str, object]] = Field(default_factory=list)
    instability_clusters: list[dict[str, object]] = Field(default_factory=list)
    recovery_failure_patterns: list[dict[str, object]] = Field(default_factory=list)
    summary: str
