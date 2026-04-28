from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from models.lab_result import LabResult
from models.notification import Notification, NotificationTypeEnum
from models.user import User
from models.user_vital import UserVital, UserVitalTypeEnum
from routes.users import get_current_user_from_header

router = APIRouter(prefix="/api/v1/health", tags=["Health Timeline"])


def _vital_title(vital_type: UserVitalTypeEnum) -> str:
    mapping = {
        UserVitalTypeEnum.STEPS: "Steps Logged",
        UserVitalTypeEnum.SLEEP: "Sleep Logged",
        UserVitalTypeEnum.HEART_RATE: "Heart Rate Logged",
        UserVitalTypeEnum.SPO2: "SpO2 Logged",
        UserVitalTypeEnum.BLOOD_PRESSURE_SYSTOLIC: "Blood Pressure Logged",
        UserVitalTypeEnum.BLOOD_PRESSURE_DIASTOLIC: "Blood Pressure Logged",
    }
    return mapping.get(vital_type, "Wearable Metric Logged")


@router.get("/timeline")
def get_timeline(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    user_id = current_user.id

    vitals, labs, alerts = [], [], []

    try:
        vitals = (
            db.query(UserVital)
            .filter(UserVital.user_id == user_id)
            .order_by(UserVital.timestamp.desc())
            .limit(60)
            .all()
        )
    except Exception as e:
        print(f"Error fetching user_vitals for timeline: {e}")

    try:
        labs = (
            db.query(LabResult)
            .filter(LabResult.user_id == user_id)
            .order_by(LabResult.timestamp.desc())
            .limit(30)
            .all()
        )
    except Exception as e:
        print(f"Error fetching labs for timeline: {e}")

    try:
        alerts = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.notification_type == NotificationTypeEnum.HEALTH_ALERT,
            )
            .order_by(Notification.created_at.desc())
            .limit(30)
            .all()
        )
    except Exception as e:
        print(f"Error fetching alerts for timeline: {e}")

    timeline_events = []

    for vital in vitals:
        vital_type = vital.vital_type.value if hasattr(vital.vital_type, "value") else str(vital.vital_type)
        label = vital_type.replace("_", " ").title()
        timeline_events.append(
            {
                "id": f"vital_{vital.id}",
                "type": "Vitals",
                "source": "user_vitals",
                "title": _vital_title(vital.vital_type),
                "description": f"{label}: {vital.value} {vital.unit or ''}".strip(),
                "timestamp": vital.timestamp.isoformat() if vital.timestamp else None,
                "metrics": [
                    {
                        "label": label,
                        "value": f"{vital.value} {vital.unit or ''}".strip(),
                    }
                ],
            }
        )

    for lab in labs:
        color = "bg-green-500"
        if lab.status and lab.status.lower() in ["high", "low", "abnormal", "critical"]:
            color = "bg-amber-500"
        if lab.status and lab.status.lower() == "critical":
            color = "bg-red-500"

        timeline_events.append(
            {
                "id": f"lab_{lab.id}",
                "type": "Tests",
                "source": "lab",
                "category": lab.category,
                "title": f"Lab Result: {lab.name}",
                "description": f"Result: {lab.value} {lab.unit or ''} (Status: {lab.status or 'info'})",
                "timestamp": lab.timestamp.isoformat() if lab.timestamp else None,
                "labData": [
                    {
                        "label": lab.name,
                        "value": f"{lab.value} {lab.unit or ''}",
                        "progress": 50,
                        "color": color,
                    }
                ],
            }
        )

    for alert in alerts:
        severity_val = alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
        timeline_events.append(
            {
                "id": f"alert_{alert.id}",
                "type": "Alerts",
                "source": "system",
                "title": alert.title,
                "description": alert.description,
                "timestamp": alert.created_at.isoformat() if alert.created_at else None,
                "metrics": [
                    {"label": "Severity", "value": severity_val.upper()}
                ],
            }
        )

    timeline_events.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    return {
        "success": True,
        "status": "ready" if timeline_events else "empty",
        "source": "db",
        "error": None,
        "data": timeline_events,
        "last_updated": timeline_events[0]["timestamp"] if timeline_events else None,
    }
