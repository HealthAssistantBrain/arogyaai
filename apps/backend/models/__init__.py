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
from .user_profile    import UserProfile
from .health_profile  import HealthProfile, GenderEnum
from .device          import Device, DeviceTypeEnum
from .vitals_data     import VitalsData
from .wearable_data   import WearableData
from .medical_history import MedicalHistory
from .report          import Report, ReportTypeEnum, ReportStatusEnum
from .risk_score      import RiskScore, RiskLevelEnum
from .recommendation  import Recommendation, RecCategoryEnum, PriorityEnum
from .feature_snapshot import FeatureSnapshotRecord
from .baseline_metric import BaselineMetricRecord
from .lab_value      import LabValue
from .shap_value     import ShapValueRecord
from .health_score   import HealthScoreRecord
from .alert           import Alert, AlertTypeEnum, SeverityEnum
from .notification    import Notification, NotificationTypeEnum, NotificationSeverityEnum
from .user_device     import (
    PROVIDER_APPLE_HEALTH,
    PROVIDER_FITBIT,
    PROVIDER_GOOGLE_FIT,
    UserDevice,
    UserDeviceProviderEnum,
)
from .user_vital      import UserVital, UserVitalTypeEnum, UserVitalSourceEnum
from .user_setting    import UserSetting
from .session         import Session
from .log             import Log
from .google_fit_connection import GoogleFitConnection
from .lab_result          import LabResult

__all__ = [
    # Core Base
    "Base",
    # Domain Models
    "User",
    "UserProfile",
    "HealthProfile",
    "Device",
    "VitalsData",
    "WearableData",
    "MedicalHistory",
    "Report",
    "RiskScore",
    "Recommendation",
    "FeatureSnapshotRecord",
    "BaselineMetricRecord",
    "LabValue",
    "ShapValueRecord",
    "HealthScoreRecord",
    "Alert",
    "Notification",
    "UserDevice",
    "UserVital",
    "UserSetting",
    "Session",
    "Log",
    "GoogleFitConnection",
    "LabResult",
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
    "NotificationTypeEnum",
    "NotificationSeverityEnum",
    "UserDeviceProviderEnum",
    "PROVIDER_GOOGLE_FIT",
    "PROVIDER_APPLE_HEALTH",
    "PROVIDER_FITBIT",
    "UserVitalTypeEnum",
    "UserVitalSourceEnum",
]
