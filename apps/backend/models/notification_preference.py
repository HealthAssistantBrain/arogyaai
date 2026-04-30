"""
NotificationPreference model — persisted per-user delivery preferences.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class NotificationPreference(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    push_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    ai_insights_email = Column(Boolean, nullable=False, default=True, server_default="true")
    ai_insights_push = Column(Boolean, nullable=False, default=True, server_default="true")
    health_alerts_email = Column(Boolean, nullable=False, default=True, server_default="true")
    health_alerts_push = Column(Boolean, nullable=False, default=True, server_default="true")
    reminders_email = Column(Boolean, nullable=False, default=True, server_default="true")
    reminders_push = Column(Boolean, nullable=False, default=True, server_default="true")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="notification_preferences")
