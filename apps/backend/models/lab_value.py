"""
LabValue model — maps to the `lab_values` table.
Stores extracted biomarkers from uploaded reports.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LabValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lab_values"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True)
    biomarker_name = Column(String(255), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(50))
    reference_range = Column(String(100))
    category = Column(String(50), index=True)
    status = Column(String(20))
    raw_text = Column(String(2000))
    extracted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="lab_values")
    report = relationship("Report", back_populates="lab_values")
