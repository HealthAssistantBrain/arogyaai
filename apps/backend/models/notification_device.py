"""
NotificationDevice model — browser/web-push subscriptions per user device.
"""
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class NotificationDevice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_devices"
    __table_args__ = (
        UniqueConstraint("device_token", name="uq_notification_devices_device_token"),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_token = Column(Text, nullable=False)
    device_name = Column(String(120), nullable=True)
    platform = Column(String(50), nullable=False, default="web", server_default="web")
    subscription = Column(JSONB, nullable=False, default=dict)
    last_active = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    user = relationship("User", back_populates="notification_devices")
