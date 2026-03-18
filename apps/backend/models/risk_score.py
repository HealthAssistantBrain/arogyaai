"""
RiskScore model — maps to the `risk_scores` table.
1:1 with Report. 1:N to Recommendations.
"""
import enum

from sqlalchemy import Column, String, Numeric, Enum, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
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

    report_id        = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), unique=True, nullable=False)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_level       = Column(Enum(RiskLevelEnum, name="risk_level_enum"), nullable=False, index=True)
    overall_score    = Column(Numeric(5, 2), nullable=False)
    confidence_score = Column(Numeric(5, 2))
    ml_model_version = Column(String(50))
    calculated_at    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Relationships ──────────────────────────────────────────
    report          = relationship("Report", back_populates="risk_score")
    user            = relationship("User", back_populates="risk_scores")
    recommendations = relationship("Recommendation", back_populates="risk_score")
