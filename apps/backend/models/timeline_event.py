"""
Timeline event model for persisted clinical timeline entries.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TimelineEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "timeline_events"
    __table_args__ = (
        UniqueConstraint("user_id", "type", "reference_id", name="uq_timeline_events_user_type_reference"),
        Index("ix_timeline_events_user_timestamp", "user_id", "timestamp"),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    title = Column(Text, nullable=False)
    reference_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    event_metadata = Column("metadata", JSONB, nullable=True, default=dict)

    user = relationship("User", back_populates="timeline_events")
