from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    HEALTH = "health"
    EMOTIONAL = "emotional"
    SUMMARY = "summary"


class MemoryImportance(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRIVIAL = "trivial"


class EmotionalTone(str, Enum):
    ANXIOUS = "anxious"
    REASSURED = "reassured"
    DISTRESSED = "distressed"
    CALM = "calm"
    FRUSTRATED = "frustrated"
    HOPEFUL = "hopeful"
    NEUTRAL = "neutral"
    CONCERNED = "concerned"


@dataclass
class MemoryItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    memory_type: MemoryType = MemoryType.EPISODIC
    importance: MemoryImportance = MemoryImportance.MEDIUM
    content: str = ""
    structured_data: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    last_accessed: datetime | None = None
    access_count: int = 0
    decay_score: float = 1.0
    embedding_id: str | None = None
    session_id: str | None = None
    is_encrypted: bool = False
    consent_level: str = "standard"


@dataclass
class EpisodicMemory(MemoryItem):
    interaction_summary: str = ""
    symptoms_discussed: list[str] = field(default_factory=list)
    recommendations_given: list[str] = field(default_factory=list)
    reports_analyzed: list[str] = field(default_factory=list)
    outcome_noted: str | None = None
    follow_up_needed: bool = False


@dataclass
class SemanticMemory(MemoryItem):
    preferred_explanation_depth: str = "moderate"
    preferred_tone: str = "warm"
    health_literacy_level: str = "medium"
    recurring_concerns: list[str] = field(default_factory=list)
    communication_preferences: dict[str, Any] = field(default_factory=dict)
    confirmed_conditions: list[str] = field(default_factory=list)
    known_allergies: list[str] = field(default_factory=list)
    lifestyle_notes: list[str] = field(default_factory=list)
    updated_at: datetime | None = None


@dataclass
class HealthMemory(MemoryItem):
    metric_name: str = ""
    metric_value: float | None = None
    metric_unit: str = ""
    trend_direction: str = "stable"
    trend_note: str = ""
    disease_context: str | None = None
    source: str = "wearable"
    risk_level: str = "low"


@dataclass
class EmotionalMemory(MemoryItem):
    emotional_tone: EmotionalTone = EmotionalTone.NEUTRAL
    trigger_topic: str = ""
    intensity: float = 0.5
    adaptation_applied: str = ""
    resolved: bool = False


@dataclass
class RetrievedMemoryContext:
    short_term: list[MemoryItem] = field(default_factory=list)
    episodic: list[EpisodicMemory] = field(default_factory=list)
    semantic: SemanticMemory | None = None
    health_trends: list[HealthMemory] = field(default_factory=list)
    emotional: EmotionalMemory | None = field(default=None)
    summaries: list[MemoryItem] = field(default_factory=list)
    token_estimate: int = 0
    retrieval_time_ms: float = 0.0

    def to_prompt_string(self) -> str:
        parts: list[str] = []
        if self.semantic:
            parts.append(_format_semantic(self.semantic))
        if self.episodic:
            parts.append(_format_episodic(self.episodic[:3]))
        if self.health_trends:
            parts.append(_format_health_trends(self.health_trends[:4]))
        if self.emotional:
            parts.append(_format_emotional(self.emotional))
        if self.summaries:
            parts.append(_format_summaries(self.summaries[:2]))
        if not parts:
            return ""
        return "=== PERSONAL HEALTH MEMORY ===\n" + "\n\n".join(parts) + "\n=== END MEMORY ==="

    def to_metadata(self) -> dict[str, Any]:
        return {
            "token_count": self.token_estimate,
            "episodic_count": len(self.episodic),
            "has_health_trends": bool(self.health_trends),
            "has_emotional_context": bool(self.emotional),
            "retrieval_ms": round(self.retrieval_time_ms, 2),
        }


def _format_semantic(memory: SemanticMemory) -> str:
    lines = ["[User Profile]"]
    if memory.confirmed_conditions:
        lines.append(f"Known conditions: {', '.join(memory.confirmed_conditions[:4])}")
    if memory.known_allergies:
        lines.append(f"Known allergies: {', '.join(memory.known_allergies[:4])}")
    if memory.recurring_concerns:
        lines.append(f"Recurring concerns: {', '.join(memory.recurring_concerns[:3])}")
    if memory.lifestyle_notes:
        lines.append(f"Lifestyle notes: {'; '.join(memory.lifestyle_notes[:3])}")
    lines.append(f"Preferred explanation depth: {memory.preferred_explanation_depth}")
    lines.append(f"Preferred tone: {memory.preferred_tone}")
    return "\n".join(lines)


def _format_episodic(items: list[EpisodicMemory]) -> str:
    lines = ["[Prior Interactions]"]
    for item in items:
        lines.append(f"{item.created_at.strftime('%b %d, %Y')}: {item.interaction_summary}")
        if item.symptoms_discussed:
            lines.append(f"Symptoms: {', '.join(item.symptoms_discussed[:4])}")
        if item.recommendations_given:
            lines.append(f"Advice given: {'; '.join(item.recommendations_given[:2])}")
        if item.follow_up_needed:
            lines.append("Follow-up was recommended.")
    return "\n".join(lines)


def _format_health_trends(items: list[HealthMemory]) -> str:
    lines = ["[Health Trends]"]
    arrows = {"improving": "up", "worsening": "down", "stable": "flat"}
    for item in items:
        lines.append(
            f"{item.metric_name}: {item.metric_value} {item.metric_unit} "
            f"({item.created_at.strftime('%b %d')}, {arrows.get(item.trend_direction, 'flat')} {item.trend_direction})"
        )
        if item.trend_note:
            lines.append(f"Note: {item.trend_note}")
    return "\n".join(lines)


def _format_emotional(memory: EmotionalMemory) -> str:
    lines = ["[Emotional Context]"]
    lines.append(
        f"User previously felt {memory.emotional_tone.value} discussing {memory.trigger_topic or 'general health'}."
    )
    if memory.intensity >= 0.7:
        lines.append("Answer with extra reassurance and care.")
    return "\n".join(lines)


def _format_summaries(items: list[MemoryItem]) -> str:
    return "[Health Journey Summary]\n" + "\n".join(item.content for item in items if item.content)


MEMORY_TOKEN_BUDGET = 800
QDRANT_MEMORY_COLLECTION = "arogyaai_memory"
REDIS_SHORT_TERM_TTL_SECONDS = 7200
MEMORY_DECAY_HALF_LIFE_DAYS = 30
