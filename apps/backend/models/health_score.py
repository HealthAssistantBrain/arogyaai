"""
HealthScoreRecord model — maps to the `health_scores` table.
Stores the composite health score derived from risk, lifestyle, vitals, and sleep.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class HealthScoreRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "health_scores"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_score_id = Column(UUID(as_uuid=True), ForeignKey("risk_scores.id", ondelete="SET NULL"), nullable=True, index=True)
    score = Column(Numeric(5, 2), nullable=False)
    risk_component = Column(Numeric(5, 2))
    lifestyle_component = Column(Numeric(5, 2))
    vitals_component = Column(Numeric(5, 2))
    sleep_component = Column(Numeric(5, 2))
    health_payload = Column(JSONB, nullable=True)
    source = Column(String(40), default="pipeline")
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="health_scores")
    risk_score = relationship("RiskScore", back_populates="health_scores")
