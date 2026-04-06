"""
UserDevice model — canonical storage for connected providers and OAuth tokens.
"""
import enum

from sqlalchemy import Column, DateTime, Text, Boolean, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


PROVIDER_GOOGLE_FIT = "google_fit"
PROVIDER_APPLE_HEALTH = "apple_health"
PROVIDER_FITBIT = "fitbit"


class UserDeviceProviderEnum(str, enum.Enum):
    GOOGLE_FIT = PROVIDER_GOOGLE_FIT
    APPLE_HEALTH = PROVIDER_APPLE_HEALTH
    FITBIT = PROVIDER_FITBIT


class UserDevice(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_devices"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_devices_user_provider"),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(
        Enum(
            UserDeviceProviderEnum,
            name="user_device_provider_enum",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expiry = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="user_devices")
