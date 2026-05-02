"""
WearableData model — legacy/deprecated wearable storage.
Kept mapped during the transition so older rows can be migrated and read safely.
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class WearableData(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "wearable_data"

    user_id                 = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id               = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    recorded_at             = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    step_count              = Column(Integer)
    __table_args__ = (
        Index(
            "uq_wearable_data_user_recorded_at_steps",
            "user_id",
            "recorded_at",
            unique=True,
            postgresql_where=step_count.isnot(None),
        ),
    )
    calories_burned         = Column(Numeric(8, 2))
    sleep_duration_minutes  = Column(Integer)
    sleep_score             = Column(Integer)
    created_at              = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Relationships ──────────────────────────────────────────
    user   = relationship("User", back_populates="wearable_data")
    device = relationship("Device", back_populates="wearable_data")
