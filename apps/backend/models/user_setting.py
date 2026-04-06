"""
UserSetting model — auto-fetch and sync preferences.
"""
from sqlalchemy import Column, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class UserSetting(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_settings_user_id"),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    auto_fetch_enabled = Column(Boolean, default=False, nullable=False)
    fetch_interval_minutes = Column(Integer, default=15, nullable=False)
    last_fetch_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="user_settings")
