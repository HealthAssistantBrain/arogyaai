"""
Log model — maps to the `logs` table.
Audit trail for all API actions. user_id is nullable for system-level events.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class Log(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "logs"

    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action     = Column(String(100), nullable=False)
    endpoint   = Column(String(255))
    ip_address = Column(String(45))
    details    = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # ── Relationships ──────────────────────────────────────────
    user = relationship("User", back_populates="logs")
