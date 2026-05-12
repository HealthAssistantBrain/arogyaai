from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ClinicalWindowSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    label: str
    narrative: str
    highlights: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class CompressedTrend(BaseModel):
    model_config = ConfigDict(extra="allow")

    metric: str
    label: str
    direction: str
    state: str
    latest_value: float | None = None
    baseline_value: float | None = None
    delta: float = 0.0
    unit: str | None = None
    interpretation: str
    clinical_relevance: str


class RiskPriority(BaseModel):
    model_config = ConfigDict(extra="allow")

    label: str
    severity: str
    score: float
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)


class InterventionOutcome(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    category: str
    status: str
    effectiveness_score: float
    narrative: str
    evidence_ids: list[str] = Field(default_factory=list)


class ClinicalSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    patient_id: str
    generated_at: str
    overview: str
    summary_7d: ClinicalWindowSummary
    summary_30d: ClinicalWindowSummary
    long_term_narrative: ClinicalWindowSummary
    deterioration_summary: ClinicalWindowSummary
    recovery_summary: ClinicalWindowSummary
    physiological_compression: list[CompressedTrend] = Field(default_factory=list)
    risk_priorities: list[RiskPriority] = Field(default_factory=list)
    consultation_preparation: dict[str, object] = Field(default_factory=dict)
    intervention_outcomes: list[InterventionOutcome] = Field(default_factory=list)
    safety: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)
