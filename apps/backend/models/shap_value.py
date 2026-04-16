"""
ShapValueRecord model — maps to the `shap_values` table.
Stores model SHAP values or rule-based SHAP-like driver attributions.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ShapValueRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shap_values"

    prediction_id = Column(UUID(as_uuid=True), ForeignKey("risk_scores.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_name = Column(String(120), nullable=False, index=True)
    shap_value = Column(Numeric(10, 4), nullable=False)
    abs_shap_value = Column(Numeric(10, 4), nullable=False)
    direction = Column(String(20), nullable=False)
    explanation = Column(String(500))
    source_type = Column(String(30), default="rule_fallback")
    shap_payload = Column(JSONB, nullable=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    prediction = relationship("RiskScore", back_populates="shap_values")
    user = relationship("User", back_populates="shap_values")
