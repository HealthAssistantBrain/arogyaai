"""
Device model — maps to the `devices` table.
1:N from User, 1:N to WearableData.
"""
import enum

from sqlalchemy import Column, String, Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class DeviceTypeEnum(str, enum.Enum):
    SMARTWATCH     = "SMARTWATCH"
    FITNESS_BAND   = "FITNESS_BAND"
    BPMONITOR      = "BPMONITOR"
    GLUCOMETER     = "GLUCOMETER"
    WEIGHING_SCALE = "WEIGHING_SCALE"
    OTHER          = "OTHER"


class Device(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "devices"

    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_type = Column(Enum(DeviceTypeEnum, name="device_type_enum"), nullable=False)
    device_name = Column(String(100))
    mac_address = Column(String(50), unique=True)
    is_active   = Column(Boolean, default=True)

    # ── Relationships ──────────────────────────────────────────
    user          = relationship("User", back_populates="devices")
    wearable_data = relationship("WearableData", back_populates="device")
