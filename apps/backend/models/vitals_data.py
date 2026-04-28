"""
VitalsData model — legacy/deprecated structured vitals storage.
Kept mapped during the transition so canonical `user_vitals` can backfill safely.
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class VitalsData(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "vitals_data"

    user_id                = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at            = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    heart_rate_bpm         = Column(Integer)
    blood_pressure_sys     = Column(Integer)
    blood_pressure_dia     = Column(Integer)
    oxygen_saturation_spo2 = Column(Numeric(5, 2))
    body_temperature_c     = Column(Numeric(4, 2))
    created_at             = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Relationships ──────────────────────────────────────────
    user = relationship("User", back_populates="vitals_data")
