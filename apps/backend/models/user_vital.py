"""
UserVital model — canonical storage for time-series vitals pulled from wearables.
"""
import enum

from sqlalchemy import Column, DateTime, Float, String, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class UserVitalTypeEnum(str, enum.Enum):
    HEART_RATE = "heart_rate"
    STEPS = "steps"
    SLEEP = "sleep"
    SPO2 = "spo2"
    BLOOD_PRESSURE_SYSTOLIC = "blood_pressure_systolic"
    BLOOD_PRESSURE_DIASTOLIC = "blood_pressure_diastolic"
    BODY_TEMPERATURE = "body_temperature"
    CALORIES_BURNED = "calories_burned"


class UserVitalSourceEnum(str, enum.Enum):
    GOOGLE_FIT = "google_fit"


class UserVital(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_vitals"
    __table_args__ = (
        UniqueConstraint("user_id", "type", "timestamp", "source", name="uq_user_vitals_user_type_timestamp_source"),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    vital_type = Column("type", Enum(UserVitalTypeEnum, name="user_vital_type_enum"), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(Enum(UserVitalSourceEnum, name="user_vital_source_enum"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="user_vitals")
