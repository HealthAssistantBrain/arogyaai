"""
UserProfile model — maps to the `user_profile` table.
Stores editable identity/profile fields separate from auth/session data.
"""

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text, Date
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
    supabase_id = Column(UUID(as_uuid=True), unique=True, nullable=True, index=True)
    email = Column(Text)
    full_name = Column(String(150))
    avatar_url = Column(Text)
    phone_number = Column(String(20))
    date_of_birth = Column(Date)
    age = Column(Integer)
    gender = Column(String(20))
    height_cm = Column(Numeric(5, 2))
    weight_kg = Column(Numeric(5, 2))
    activity_level = Column(Integer)
    goals = Column(Text)
    blood_group = Column(String(5))
    allergies = Column(Text)

    user = relationship("User", back_populates="user_profile")

    @property
    def phone(self):
        return self.phone_number

    @phone.setter
    def phone(self, value):
        self.phone_number = value

    @property
    def height(self):
        return self.height_cm

    @height.setter
    def height(self, value):
        self.height_cm = value

    @property
    def weight(self):
        return self.weight_kg

    @weight.setter
    def weight(self, value):
        self.weight_kg = value
