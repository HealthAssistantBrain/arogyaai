"""
Report model — maps to the `reports` table.
1:N from User. 1:1 to RiskScore.
"""
import enum

from sqlalchemy import Column, String, Text, Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
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

    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type = Column(Enum(ReportTypeEnum, name="report_type_enum"), nullable=False)
    file_url    = Column(Text, nullable=False)
    parsed_text = Column(Text)
    status      = Column(Enum(ReportStatusEnum, name="report_status_enum"), default=ReportStatusEnum.PENDING, index=True)
    is_deleted  = Column(Boolean, default=False)

    # ── Relationships ──────────────────────────────────────────
    user       = relationship("User", back_populates="reports")
    risk_score = relationship("RiskScore", back_populates="report", uselist=False)
    lab_values = relationship("LabValue", back_populates="report")
    feature_snapshots = relationship("FeatureSnapshotRecord", back_populates="report")
