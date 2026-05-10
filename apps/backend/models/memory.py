from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from .base import Base, UUIDPrimaryKeyMixin


class EpisodicMemoryRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "episodic_memory"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(Text, nullable=True)
    interaction_summary = Column(Text, nullable=False)
    symptoms_discussed = Column(ARRAY(Text), nullable=True)
    recommendations_given = Column(ARRAY(Text), nullable=True)
    reports_analyzed = Column(ARRAY(Text), nullable=True)
    outcome_noted = Column(Text, nullable=True)
    follow_up_needed = Column(Boolean, nullable=False, server_default=text("false"))
    importance = Column(Text, nullable=False, server_default=text("'medium'"))
    decay_score = Column(Float, nullable=False, server_default=text("1.0"))
    embedding_id = Column(Text, nullable=True)
    tags = Column(ARRAY(Text), nullable=True)
    consent_level = Column(Text, nullable=False, server_default=text("'standard'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    access_count = Column(Integer, nullable=False, server_default=text("0"))
    is_encrypted = Column(Boolean, nullable=False, server_default=text("false"))


class SemanticMemoryRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "semantic_memory"
    __table_args__ = (UniqueConstraint("user_id", name="uq_semantic_memory_user_id"),)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    preferred_explanation_depth = Column(Text, nullable=False, server_default=text("'moderate'"))
    preferred_tone = Column(Text, nullable=False, server_default=text("'warm'"))
    health_literacy_level = Column(Text, nullable=False, server_default=text("'medium'"))
    recurring_concerns = Column(ARRAY(Text), nullable=True)
    confirmed_conditions = Column(ARRAY(Text), nullable=True)
    known_allergies = Column(ARRAY(Text), nullable=True)
    lifestyle_notes = Column(ARRAY(Text), nullable=True)
    communication_preferences = Column(JSONB(astext_type=Text()), nullable=False, server_default=text("'{}'::jsonb"))
    embedding_id = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class HealthMemoryRecord(Base):
    __tablename__ = "health_memory"
    __table_args__ = (
        Index("ix_health_memory_id", "id"),
        Index("ix_health_memory_user_created_at", "user_id", "created_at"),
        Index("ix_health_memory_user_metric_created_at", "user_id", "metric_name", "created_at"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        server_default=func.gen_random_uuid(),
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name = Column(Text, nullable=False, index=True)
    metric_value = Column(Float, nullable=True)
    metric_unit = Column(Text, nullable=True)
    trend_direction = Column(Text, nullable=False, server_default=text("'stable'"))
    trend_note = Column(Text, nullable=True)
    disease_context = Column(Text, nullable=True)
    source = Column(Text, nullable=False, server_default=text("'wearable'"))
    risk_level = Column(Text, nullable=False, server_default=text("'low'"))
    importance = Column(Text, nullable=False, server_default=text("'medium'"))
    decay_score = Column(Float, nullable=False, server_default=text("1.0"))
    embedding_id = Column(Text, nullable=True)
    tags = Column(ARRAY(Text), nullable=True)
    created_at = Column(DateTime(timezone=True), primary_key=True, nullable=False, server_default=func.now(), index=True)


class EmotionalMemoryRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "emotional_memory"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    emotional_tone = Column(Text, nullable=False)
    trigger_topic = Column(Text, nullable=True)
    intensity = Column(Float, nullable=False, server_default=text("0.5"))
    adaptation_applied = Column(Text, nullable=True)
    resolved = Column(Boolean, nullable=False, server_default=text("false"))
    session_id = Column(Text, nullable=True)
    embedding_id = Column(Text, nullable=True)
    decay_score = Column(Float, nullable=False, server_default=text("1.0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class MemorySummaryRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "memory_summaries"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    summary_type = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    covers_from = Column(DateTime(timezone=True), nullable=True)
    covers_to = Column(DateTime(timezone=True), nullable=True)
    source_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    embedding_id = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class MemoryAuditLogRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "memory_audit_log"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(Text, nullable=False)
    memory_type = Column(Text, nullable=True)
    memory_id = Column(UUID(as_uuid=True), nullable=True)
    metadata_json = Column("metadata", JSONB(astext_type=Text()), nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
