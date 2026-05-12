from __future__ import annotations

from pydantic import BaseModel, Field


class ConversationalMemorySnapshot(BaseModel):
    active_threads: list[str] = Field(default_factory=list)
    unresolved_threads: list[str] = Field(default_factory=list)
    prior_recommendations: list[str] = Field(default_factory=list)
    continuity_reference: str = ""
    session_summary: str = ""


class SymptomMemorySnapshot(BaseModel):
    active_symptoms: list[str] = Field(default_factory=list)
    recurring_symptoms: list[str] = Field(default_factory=list)
    prior_symptoms: list[str] = Field(default_factory=list)
    baseline_signals: list[str] = Field(default_factory=list)
    trend_signals: list[str] = Field(default_factory=list)
    anomaly_progression: list[str] = Field(default_factory=list)
    recovery_trajectory: list[str] = Field(default_factory=list)


class BehavioralMemorySnapshot(BaseModel):
    explanation_preference: str = "balanced"
    communication_style: str = "calm"
    pacing_preference: str = "steady"
    question_tolerance: str = "focused"
    reassurance_preference: str = "measured"
    user_state: str = "neutral"


class NarrativeMemorySnapshot(BaseModel):
    longitudinal_summary: str = ""
    prior_discussions: list[str] = Field(default_factory=list)
    assistant_highlights: list[str] = Field(default_factory=list)
    user_highlights: list[str] = Field(default_factory=list)


class TopicMemorySnapshot(BaseModel):
    active_topics: list[str] = Field(default_factory=list)
    recurring_topics: list[str] = Field(default_factory=list)
    resolved_topics: list[str] = Field(default_factory=list)
    last_followup_topics: list[str] = Field(default_factory=list)


class MemorySnapshot(BaseModel):
    conversational: ConversationalMemorySnapshot = Field(default_factory=ConversationalMemorySnapshot)
    symptom: SymptomMemorySnapshot = Field(default_factory=SymptomMemorySnapshot)
    behavioral: BehavioralMemorySnapshot = Field(default_factory=BehavioralMemorySnapshot)
    narrative: NarrativeMemorySnapshot = Field(default_factory=NarrativeMemorySnapshot)
    topic: TopicMemorySnapshot = Field(default_factory=TopicMemorySnapshot)
    compressed_summary: str = ""
    has_longitudinal_context: bool = False
    retrieval_counts: dict[str, int] = Field(default_factory=dict)

    def to_prompt_payload(self) -> dict[str, object]:
        return {
            "continuity_reference": self.conversational.continuity_reference,
            "active_threads": self.conversational.active_threads[:3],
            "unresolved_threads": self.conversational.unresolved_threads[:3],
            "active_symptoms": self.symptom.active_symptoms[:4],
            "baseline_signals": self.symptom.baseline_signals[:3],
            "trend_signals": self.symptom.trend_signals[:3],
            "recovery_trajectory": self.symptom.recovery_trajectory[:2],
            "behavioral_preferences": {
                "explanation_preference": self.behavioral.explanation_preference,
                "pacing_preference": self.behavioral.pacing_preference,
                "reassurance_preference": self.behavioral.reassurance_preference,
            },
            "active_topics": self.topic.active_topics[:4],
            "recurring_topics": self.topic.recurring_topics[:3],
            "memory_summary": self.compressed_summary,
        }
