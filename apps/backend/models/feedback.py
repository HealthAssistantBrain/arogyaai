"""
Feedback model for user corrections, ratings, and usefulness signals.
"""
from __future__ import annotations

import enum

from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


def _enum_values(enum_cls):
    return [member.value for member in enum_cls]


class FeedbackEntityType(str, enum.Enum):
    PREDICTION = "prediction"
    EXPLANATION = "explanation"
    RECOMMENDATION = "recommendation"
    ANOMALY = "anomaly"


class FeedbackType(str, enum.Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIAL = "partial"
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"


class Feedback(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_feedback_rating_1_5"),
        Index("ix_feedback_user_entity", "user_id", "entity_type", "entity_id"),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(
        Enum(
            FeedbackEntityType,
            name="feedback_entity_type_enum",
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    rating = Column(Integer, nullable=True)
    feedback_type = Column(
        Enum(
            FeedbackType,
            name="feedback_type_enum",
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    comment = Column(Text, nullable=True)
    feedback_metadata = Column("metadata", JSONB, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="feedback")
