"""
RiskScore model — maps to the `risk_scores` table.
Can be linked to a report or used as a standalone prediction record.
"""
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin


class RiskLevelEnum(str, enum.Enum):
    LOW      = "LOW"
    MODERATE = "MODERATE"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN  = "UNKNOWN"


class RiskScore(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "risk_scores"

    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), unique=True, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_level = Column(Enum(RiskLevelEnum, name="risk_level_enum"), nullable=False, index=True)
    overall_score = Column(Numeric(5, 2), nullable=False)
    confidence_score = Column(Numeric(5, 2))
    ml_model_version = Column(String(50))
    prediction_source = Column(String(40), default="rule_engine")
    prediction_status = Column(String(20), default="ready")
    feature_snapshot = Column(JSONB, nullable=True)
    risk_payload = Column(JSONB, nullable=True)
    health_score = Column(Numeric(5, 2))
    pipeline_run_id = Column(String(64))
    is_fallback = Column(Boolean, default=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Relationships ──────────────────────────────────────────
    report = relationship("Report", back_populates="risk_score")
    user = relationship("User", back_populates="risk_scores")
    recommendations = relationship("Recommendation", back_populates="risk_score")
    shap_values = relationship("ShapValueRecord", back_populates="prediction")
    health_scores = relationship("HealthScoreRecord", back_populates="risk_score")
