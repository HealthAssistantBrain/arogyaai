"""
HealthProfile model — maps to the `health_profiles` table.
1:1 relationship with User.
"""
import enum

from sqlalchemy import Column, String, Date, Numeric, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class GenderEnum(str, enum.Enum):
    MALE             = "MALE"
    FEMALE           = "FEMALE"
    OTHER            = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"


class HealthProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "health_profiles"

    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    date_of_birth = Column(Date)
    gender        = Column(Enum(GenderEnum, name="gender_enum"))
    blood_group   = Column(String(5))
    height_cm     = Column(Numeric(5, 2))
    weight_kg     = Column(Numeric(5, 2))
    allergies     = Column(ARRAY(String))

    # ── Relationship ───────────────────────────────────────────
    user = relationship("User", back_populates="health_profile")
