"""
MedicalHistory model — maps to the `medical_history` table.
1:N from User.
"""
from sqlalchemy import Column, String, Date, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class MedicalHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "medical_history"

    user_id            = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    condition_name     = Column(String(200), nullable=False)
    diagnosis_date     = Column(Date)
    treatment_details  = Column(Text)
    is_chronic         = Column(Boolean, default=False)
    is_deleted         = Column(Boolean, default=False)

    # ── Relationships ──────────────────────────────────────────
    user = relationship("User", back_populates="medical_history")
