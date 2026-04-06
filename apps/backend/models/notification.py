"""
Notification model — maps to the `notifications` table.
"""
import enum

from sqlalchemy import Column, String, Text, Boolean, Enum, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class NotificationTypeEnum(str, enum.Enum):
    AI_INSIGHT = "ai_insight"
    HEALTH_ALERT = "health_alert"
    APPOINTMENT = "appointment"
    SYSTEM = "system"


class NotificationSeverityEnum(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Notification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column("type", Enum(NotificationTypeEnum, name="notification_type_enum"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(NotificationSeverityEnum, name="notification_severity_enum"), nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="notifications")
