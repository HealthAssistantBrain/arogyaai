"""
Persisted AI-generated longitudinal reports.
"""
from sqlalchemy import Column, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GeneratedReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "generated_reports"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    status = Column(String(24), nullable=False, default="ready", server_default="ready")
    generation_type = Column(String(48), nullable=False, default="longitudinal_summary", server_default="longitudinal_summary")
    source_snapshot = Column(JSONB(astext_type=Text()), nullable=False, default=dict)
    report_payload = Column(JSONB(astext_type=Text()), nullable=False, default=dict)
    summary = Column(Text, nullable=True)
    recommendations = Column(JSONB(astext_type=Text()), nullable=False, default=list)
    confidence_score = Column(Numeric(4, 2), nullable=True)
    timeline_event_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    user = relationship("User", back_populates="generated_reports")
