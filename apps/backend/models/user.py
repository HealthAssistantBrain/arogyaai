"""
User model — maps to the `users` table.
"""
import enum

from sqlalchemy import Column, String, Boolean, Enum, Integer, Numeric
from sqlalchemy.orm import relationship

from .base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    

    email          = Column(String(255), unique=True, nullable=False, index=True)
    password_hash  = Column(String(255), nullable=False)
    full_name      = Column(String(150))
    is_email_verified  = Column(Boolean, default=False, nullable=False)
    is_onboarding_done = Column(Boolean, default=False, nullable=False)
    onboarding_step    = Column(Integer, default=1, nullable=False)
    gmail_connected    = Column(Boolean, default=False, nullable=False)
    apple_connected    = Column(Boolean, default=False, nullable=False)
    is_deleted         = Column(Boolean, default=False, nullable=False)
    
    # ── Tracking ───────────────────────────────────────────────
    health_score         = Column(Numeric(5, 2), default=0.0)
    score_change_percent  = Column(Numeric(5, 2), default=0.0)

    # ── Relationships ──────────────────────────────────────────
    user_profile    = relationship("UserProfile", back_populates="user", uselist=False)
    devices         = relationship("Device", back_populates="user")
    vitals_data     = relationship("VitalsData", back_populates="user")
    wearable_data   = relationship("WearableData", back_populates="user")
    medical_history = relationship("MedicalHistory", back_populates="user")
    reports         = relationship("Report", back_populates="user")
    risk_scores     = relationship("RiskScore", back_populates="user")
    alerts          = relationship("Alert", back_populates="user")
    notifications   = relationship("Notification", back_populates="user")
    user_devices    = relationship("UserDevice", back_populates="user")
    user_vitals     = relationship("UserVital", back_populates="user")
    user_settings   = relationship("UserSetting", back_populates="user", uselist=False)
    sessions        = relationship("Session", back_populates="user")
    logs            = relationship("Log", back_populates="user")
    google_fit_connection = relationship("GoogleFitConnection", back_populates="user", uselist=False)
    lab_results          = relationship("LabResult", back_populates="user")
    feature_snapshots    = relationship("FeatureSnapshotRecord", back_populates="user")
    baseline_metrics     = relationship("BaselineMetricRecord", back_populates="user")
    shap_values          = relationship("ShapValueRecord", back_populates="user")
    health_scores        = relationship("HealthScoreRecord", back_populates="user")

    @property
    def health_profile(self):
        return self.user_profile

    @property
    def lab_values(self):
        return self.lab_results

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"
