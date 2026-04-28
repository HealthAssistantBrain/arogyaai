"""
FeatureSnapshotRecord model — maps to the `feature_snapshots` table.
Stores the persisted feature store output used by the ML and rule pipelines.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FeatureSnapshotRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "feature_snapshots"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True)
    hr_mean_7d = Column(Numeric(6, 2))
    steps_avg_7d = Column(Numeric(10, 2))
    sleep_efficiency = Column(Numeric(5, 2))
    bmi = Column(Numeric(5, 2))
    lifestyle_score = Column(Numeric(5, 2))
    activity_score = Column(Numeric(5, 2))
    sleep_score = Column(Numeric(5, 2))
    confidence = Column(Numeric(5, 2))
    latest_observation_at = Column(DateTime(timezone=True))
    feature_payload = Column(JSONB, nullable=True)
    source_breakdown = Column(JSONB, nullable=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="feature_snapshots")
    report = relationship("Report", back_populates="feature_snapshots")
    risk_scores = relationship("RiskScore", back_populates="feature_snapshot_record")
