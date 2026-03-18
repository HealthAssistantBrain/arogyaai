"""
Alert model — maps to the `alerts` table.
1:N from User.
"""
import enum

from sqlalchemy import Column, String, Text, Boolean, Enum, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class AlertTypeEnum(str, enum.Enum):
    VITAL_ANOMALY = "VITAL_ANOMALY"
    REPORT_READY  = "REPORT_READY"
    SYSTEM_UPDATE = "SYSTEM_UPDATE"
    REMINDER      = "REMINDER"
    SECURITY      = "SECURITY"


class SeverityEnum(str, enum.Enum):
    INFO     = "INFO"
    WARNING  = "WARNING"
    CRITICAL = "CRITICAL"


class Alert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "alerts"

    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(Enum(AlertTypeEnum, name="alert_type_enum"), nullable=False)
    severity   = Column(Enum(SeverityEnum, name="severity_enum"), nullable=False, index=True)
    title      = Column(String(200), nullable=False)
    message    = Column(Text, nullable=False)
    is_read    = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # ── Relationships ──────────────────────────────────────────
    user = relationship("User", back_populates="alerts")
