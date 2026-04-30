"""
Notification model — maps to the `notifications` table.
"""
import enum

from sqlalchemy import Column, String, Text, Boolean, Enum, ForeignKey, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class NotificationTypeEnum(str, enum.Enum):
    AI_INSIGHT = "ai_insight"
    HEALTH_ALERT = "health_alert"
    SIMULATION = "simulation"
    APPOINTMENT = "appointment"
    SYSTEM = "system"
    ACTIVITY = "activity"


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
    event_metadata = Column("metadata", JSONB, nullable=True, default=dict)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    delivery_status = Column(String(32), nullable=False, default="pending", server_default="pending", index=True)
    email_status = Column(String(32), nullable=False, default="disabled", server_default="disabled")
    push_status = Column(String(32), nullable=False, default="disabled", server_default="disabled")
    delivery_attempts = Column(Integer, nullable=False, default=0, server_default="0")
    last_delivery_error = Column(Text, nullable=True)
    queued_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="notifications")
