"""
Recommendation model — maps to the `recommendations` table.
1:N from RiskScore.
"""
import enum

from sqlalchemy import Column, Text, Enum, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class RecCategoryEnum(str, enum.Enum):
    DIET         = "DIET"
    EXERCISE     = "EXERCISE"
    MEDICATION   = "MEDICATION"
    LIFESTYLE    = "LIFESTYLE"
    CONSULTATION = "CONSULTATION"


class PriorityEnum(str, enum.Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"
    URGENT = "URGENT"


class Recommendation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recommendations"

    risk_score_id       = Column(UUID(as_uuid=True), ForeignKey("risk_scores.id", ondelete="CASCADE"), nullable=False, index=True)
    category            = Column(Enum(RecCategoryEnum, name="rec_category_enum"), nullable=False)
    priority            = Column(Enum(PriorityEnum, name="priority_enum"), default=PriorityEnum.MEDIUM)
    recommendation_text = Column(Text, nullable=False)
    created_at          = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Relationships ──────────────────────────────────────────
    risk_score = relationship("RiskScore", back_populates="recommendations")
