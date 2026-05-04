"""
WearableMetric model - raw normalized wearable time-series storage.
"""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, JSON, String, UniqueConstraint, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class WearableMetric(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "wearable_metrics"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "metric_type",
            "timestamp",
            "source",
            name="uq_wearable_metrics_user_metric_timestamp_source",
        ),
        Index("ix_wearable_metrics_user_metric_timestamp", "user_id", "metric_type", "timestamp"),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_type = Column(String(64), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(32), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(64), nullable=False, index=True, default="google_fit")
    metric_metadata = Column("metadata", JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
