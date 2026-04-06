"""
UserProfile model — maps to the `user_profile` table.
Stores editable identity/profile fields separate from auth/session data.
"""

from sqlalchemy import Column, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_profile"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    full_name = Column(String(150))
    avatar_url = Column(Text)
    height = Column(Numeric(5, 2))
    weight = Column(Numeric(5, 2))
    blood_group = Column(String(5))
    allergies = Column(Text)

    user = relationship("User", back_populates="user_profile")
