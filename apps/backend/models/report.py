"""
Report model — maps to the `reports` table.
1:N from User. Supports multiple prediction runs per report.
"""
import enum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class ReportTypeEnum(str, enum.Enum):
    BLOOD_TEST    = "BLOOD_TEST"
    MRI           = "MRI"
    XRAY          = "XRAY"
    PRESCRIPTION  = "PRESCRIPTION"
    CLINICAL_NOTE = "CLINICAL_NOTE"
    GENETIC       = "GENETIC"
    OTHER         = "OTHER"


class ReportStatusEnum(str, enum.Enum):
    PENDING    = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("user_id", "file_hash", name="uq_reports_user_file_hash"),
    )

    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type = Column(Enum(ReportTypeEnum, name="report_type_enum"), nullable=False)
    file_url    = Column(Text, nullable=False)
    file_hash = Column(String(64), nullable=True, index=True)
    original_filename = Column(Text, nullable=True)
    stored_filename = Column(Text, nullable=True)
    parsed_text = Column(Text)
    summary_data = Column(JSONB(astext_type=Text()), nullable=True)
    status      = Column(Enum(ReportStatusEnum, name="report_status_enum"), default=ReportStatusEnum.PENDING, index=True)
    is_deleted  = Column(Boolean, default=False)
    storage_bucket = Column(String(64), nullable=True)
    storage_path = Column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────
    user       = relationship("User", back_populates="reports")
    risk_scores = relationship("RiskScore", back_populates="report")
    lab_results = relationship("LabResult", back_populates="report")
    feature_snapshots = relationship("FeatureSnapshotRecord", back_populates="report")

    @property
    def risk_score(self):
        if not self.risk_scores:
            return None
        return max(
            self.risk_scores,
            key=lambda item: item.calculated_at or item.created_at,
        )

    @property
    def lab_values(self):
        return self.lab_results
