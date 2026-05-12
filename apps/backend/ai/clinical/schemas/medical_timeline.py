from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TimelineEvidence(BaseModel):
    model_config = ConfigDict(extra="allow")

    reference_id: str
    title: str
    source: str
    timestamp: str | None = None
    excerpt: str | None = None


class MedicalTimelineEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    event_type: str
    title: str
    timestamp: str | None = None
    severity: str | None = None
    narrative: str
    clinical_impact: str = "context"
    tags: list[str] = Field(default_factory=list)
    evidence: list[TimelineEvidence] = Field(default_factory=list)


class MedicalTimeline(BaseModel):
    model_config = ConfigDict(extra="allow")

    patient_id: str
    generated_at: str
    narrative: str
    recent_change_summary: str
    events: list[MedicalTimelineEntry] = Field(default_factory=list)
    anomaly_timeline: list[MedicalTimelineEntry] = Field(default_factory=list)
    deterioration_timeline: list[MedicalTimelineEntry] = Field(default_factory=list)
    intervention_timeline: list[MedicalTimelineEntry] = Field(default_factory=list)
    symptom_progression: list[MedicalTimelineEntry] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
