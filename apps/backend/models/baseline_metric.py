"""
BaselineMetricRecord model — maps to the `baseline_metrics` table.
Stores rolling window aggregates for core metrics.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaselineMetricRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "baseline_metrics"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name = Column(String(80), nullable=False, index=True)
    mean_7d = Column(Numeric(10, 2))
    mean_30d = Column(Numeric(10, 2))
    std_dev = Column(Numeric(10, 2))
    sample_count = Column(Integer, default=0)
    window_start = Column(DateTime(timezone=True))
    window_end = Column(DateTime(timezone=True))
    metric_payload = Column(JSONB, nullable=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="baseline_metrics")
