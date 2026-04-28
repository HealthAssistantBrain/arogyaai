"""
RiskScore model — prediction history table for ML/rule executions.
Each row is a single prediction run linked to a feature snapshot when available.
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

    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_snapshot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("feature_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_level = Column(Enum(RiskLevelEnum, name="risk_level_enum"), nullable=False, index=True)
    overall_score = Column(Numeric(5, 2), nullable=False)
    confidence_score = Column(Numeric(5, 2))
    model_version = Column(String(50))
    prediction_source = Column(String(40), default="rule_engine")
    prediction_status = Column(String(20), default="ready")
    risk_payload = Column(JSONB, nullable=True)
    health_score = Column(Numeric(5, 2))
    run_id = Column(String(64), index=True)
    is_fallback = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Relationships ──────────────────────────────────────────
    report = relationship("Report", back_populates="risk_scores")
    user = relationship("User", back_populates="risk_scores")
    feature_snapshot_record = relationship("FeatureSnapshotRecord", back_populates="risk_scores")
    recommendations = relationship("Recommendation", back_populates="risk_score")
    shap_values = relationship("ShapValueRecord", back_populates="prediction")
    health_scores = relationship("HealthScoreRecord", back_populates="risk_score")

    @property
    def ml_model_version(self):
        return self.model_version

    @ml_model_version.setter
    def ml_model_version(self, value):
        self.model_version = value

    @property
    def pipeline_run_id(self):
        return self.run_id

    @pipeline_run_id.setter
    def pipeline_run_id(self, value):
        self.run_id = value

    @property
    def feature_snapshot(self):
        if self.feature_snapshot_record and isinstance(self.feature_snapshot_record.feature_payload, dict):
            return self.feature_snapshot_record.feature_payload
        payload = self.risk_payload if isinstance(self.risk_payload, dict) else {}
        fallback = payload.get("feature_snapshot")
        return fallback if isinstance(fallback, dict) else None
