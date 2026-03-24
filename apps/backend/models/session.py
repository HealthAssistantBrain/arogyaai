"""
Session model — maps to the `sessions` table.
1:N from User. Manages JWT refresh token state.
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class Session(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sessions"

    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash  = Column(Text, nullable=False, index=True)
    ip_address          = Column(String(45))
    user_agent          = Column(Text)
    is_revoked          = Column(Boolean, default=False, nullable=False)
    expires_at          = Column(DateTime(timezone=True), nullable=False)
    created_at          = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Relationships ──────────────────────────────────────────
    user = relationship("User", back_populates="sessions")
