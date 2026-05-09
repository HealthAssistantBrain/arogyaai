"""
Persisted AI symptom analysis sessions for the Medical Reports Hub workflow.
"""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SymptomAnalysisSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "symptom_analysis_sessions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chief_complaint = Column(Text, nullable=False)
    duration = Column(Text, nullable=False)
    severity = Column(Integer, nullable=False)
    associated_symptoms = Column(JSONB(astext_type=Text()), nullable=False, default=list)
    aggravating_factors = Column(Text, nullable=True)
    relieving_factors = Column(Text, nullable=True)
    previous_episodes = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    symptoms_json = Column(JSONB(astext_type=Text()), nullable=False, default=dict)
    prompt_payload = Column(JSONB(astext_type=Text()), nullable=True, default=dict)
    analysis_payload = Column(JSONB(astext_type=Text()), nullable=True, default=dict)
    ai_summary = Column(Text, nullable=True)
    possible_causes = Column(JSONB(astext_type=Text()), nullable=False, default=list)
    urgency_level = Column(String(32), nullable=True)
    risk_level = Column(String(32), nullable=True)
    risk_indicators = Column(JSONB(astext_type=Text()), nullable=False, default=list)
    red_flags = Column(JSONB(astext_type=Text()), nullable=False, default=list)
    recommendations = Column(JSONB(astext_type=Text()), nullable=False, default=list)
    confidence_score = Column(Numeric(4, 2), nullable=True)
    analysis_status = Column(String(24), nullable=False, default="processing", server_default="processing")
    error_message = Column(Text, nullable=True)
    saved_to_timeline = Column(Boolean, nullable=False, default=False, server_default="false")
    timeline_event_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    user = relationship("User", back_populates="symptom_analysis_sessions")
