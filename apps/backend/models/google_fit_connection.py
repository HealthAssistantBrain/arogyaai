from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class GoogleFitConnection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "google_fit_connections"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)
    google_email = Column(String(255))
    scopes = Column(Text)
    default_timezone = Column(String(64), nullable=False, server_default="Asia/Kolkata")
    access_token_encrypted = Column(Text)
    refresh_token_encrypted = Column(Text)
    token_expires_at = Column(DateTime(timezone=True))
    last_synced_at = Column(DateTime(timezone=True))
    last_sync_status = Column(String(50))
    raw_last_response = Column(JSON)

    user = relationship("User", back_populates="google_fit_connection")
    device = relationship("Device")
