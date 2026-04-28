"""
LabResult model — maps to the `lab_results` table.
Stores individual processed lab parameter values per user per report.
"""
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class LabResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lab_results"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    reference_range = Column(String(100), nullable=True)
    category = Column(String(50), nullable=True, index=True)
    status = Column(String(20), nullable=True)
    # `timestamp` captures when the lab value was recorded (defaults to row
    # creation time so it participates in trend ordering out of the box).
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ── Relationships ──────────────────────────────────────────
    user = relationship("User", back_populates="lab_results")
    report = relationship("Report", back_populates="lab_results")

    @property
    def biomarker_name(self):
        return self.name

    @property
    def extracted_at(self):
        return self.timestamp
