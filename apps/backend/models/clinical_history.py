"""
ClinicalHistory model — maps to the `clinical_history` table.
Stores structured symptom intake and negative history.
"""
from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClinicalHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clinical_history"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chief_complaint = Column(Text, nullable=True)
    duration = Column(Text, nullable=True)
    onset = Column(Text, nullable=True)
    severity = Column(Integer, nullable=True)
    associated_symptoms = Column(JSONB(astext_type=Text()), nullable=True, default=list)
    negative_symptoms = Column(JSONB(astext_type=Text()), nullable=True, default=list)
    aggravating_factors = Column(Text, nullable=True)
    relieving_factors = Column(Text, nullable=True)
    past_history = Column(JSONB(astext_type=Text()), nullable=True, default=dict)

    user = relationship("User", back_populates="clinical_histories")
