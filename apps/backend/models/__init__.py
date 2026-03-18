"""
models/__init__.py
Centralised registry — import everything from here so that SQLAlchemy
can discover all mapped classes at startup (required for relationship() to resolve).

Usage:
    from models import User, HealthProfile, Device, ...
    from models.base import Base   # For Alembic or table creation
"""

from .base import Base

from .user            import User
from .health_profile  import HealthProfile, GenderEnum
from .device          import Device, DeviceTypeEnum
from .vitals_data     import VitalsData
from .wearable_data   import WearableData
from .medical_history import MedicalHistory
from .report          import Report, ReportTypeEnum, ReportStatusEnum
from .risk_score      import RiskScore, RiskLevelEnum
from .recommendation  import Recommendation, RecCategoryEnum, PriorityEnum
from .alert           import Alert, AlertTypeEnum, SeverityEnum
from .session         import Session
from .log             import Log

__all__ = [
    # Core Base
    "Base",
    # Domain Models
    "User",
    "HealthProfile",
    "Device",
    "VitalsData",
    "WearableData",
    "MedicalHistory",
    "Report",
    "RiskScore",
    "Recommendation",
    "Alert",
    "Session",
    "Log",
    # Enums
    "GenderEnum",
    "DeviceTypeEnum",
    "ReportTypeEnum",
    "ReportStatusEnum",
    "RiskLevelEnum",
    "RecCategoryEnum",
    "PriorityEnum",
    "AlertTypeEnum",
    "SeverityEnum",
]
