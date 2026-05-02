"""
ChatSession model — durable assistant memory for the active user chat.
"""
from sqlalchemy import Boolean, Column, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChatSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    messages = Column(JSONB(astext_type=Text()), nullable=False, default=list)
    symptoms_history = Column(JSONB(astext_type=Text()), nullable=False, default=list)
    last_risk_score = Column(Float, nullable=True)
    follow_up_pending = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="chat_sessions")
