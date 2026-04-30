from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from models.clinical_history import ClinicalHistory
from models.lab_result import LabResult
from models.notification import Notification, NotificationTypeEnum
from models.report import Report
from models.user import User
from models.user_vital import UserVital, UserVitalTypeEnum
from routes.users import get_current_user_from_header
from services.clinical_history_service import ClinicalHistoryService

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


def _event_sort_key(value: str | None) -> datetime:
    if not value:
        return datetime.min

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.min

    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


@router.get("/timeline")
def get_timeline(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    user_id = current_user.id

    vitals, labs, alerts, reports, histories = [], [], [], [], []

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

    try:
        reports = (
            db.query(Report)
            .filter(Report.user_id == user_id, Report.is_deleted == False)
            .order_by(Report.created_at.desc())
            .limit(30)
            .all()
        )
    except Exception as e:
        print(f"Error fetching reports for timeline: {e}")

    try:
        histories = (
            db.query(ClinicalHistory)
            .filter(ClinicalHistory.user_id == user_id)
            .order_by(ClinicalHistory.created_at.desc())
            .limit(30)
            .all()
        )
    except Exception as e:
        print(f"Error fetching clinical_history for timeline: {e}")

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
                "event_date": vital.timestamp.isoformat() if vital.timestamp else None,
                "metrics": [
                    {
                        "label": label,
                        "value": f"{vital.value} {vital.unit or ''}".strip(),
                    }
                ],
                "metadata": {
                    "unit": vital.unit,
                    "value": vital.value,
                    "vital_type": vital_type,
                },
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
                "event_date": lab.timestamp.isoformat() if lab.timestamp else None,
                "labData": [
                    {
                        "label": lab.name,
                        "value": f"{lab.value} {lab.unit or ''}",
                        "progress": 50,
                        "color": color,
                    }
                ],
                "metadata": {
                    "category": lab.category,
                    "name": lab.name,
                    "status": lab.status,
                    "unit": lab.unit,
                    "value": lab.value,
                },
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
                "event_date": alert.created_at.isoformat() if alert.created_at else None,
                "metrics": [
                    {"label": "Severity", "value": severity_val.upper()}
                ],
                "severity": severity_val.upper(),
                "metadata": {
                    "severity": severity_val.upper(),
                    "notification_type": (
                        alert.notification_type.value
                        if hasattr(alert.notification_type, "value")
                        else str(alert.notification_type)
                    ),
                },
            }
        )

    for report in reports:
        summary_data = report.summary_data if isinstance(report.summary_data, dict) else {}
        summary_lines = summary_data.get("summary") or []
        if isinstance(summary_lines, str):
            summary_lines = [summary_lines]
        upload_metadata = summary_data.get("upload_metadata") if isinstance(summary_data.get("upload_metadata"), dict) else {}
        report_date = upload_metadata.get("date_of_report")
        report_type = report.report_type.value if hasattr(report.report_type, "value") else str(report.report_type)
        description = next((line for line in summary_lines if line), None) or f"{report_type.replace('_', ' ').title()} uploaded for analysis."
        event_date = report_date or (report.created_at.isoformat() if report.created_at else None)

        metrics = [
            {"label": "Report Type", "value": report_type.replace("_", " ").title()},
            {"label": "Status", "value": (report.status.value if hasattr(report.status, "value") else str(report.status)).upper()},
        ]
        if report_date:
            metrics.append({"label": "Report Date", "value": report_date})

        timeline_events.append(
            {
                "id": f"report_{report.id}",
                "type": "Reports",
                "source": "report upload",
                "category": "report",
                "title": summary_data.get("title") or f"Medical Report: {report_type.replace('_', ' ').title()}",
                "description": description,
                "timestamp": report.created_at.isoformat() if report.created_at else None,
                "event_date": event_date,
                "metrics": metrics,
                "insights": summary_lines[1] if len(summary_lines) > 1 else None,
                "metadata": {
                    "report_date": report_date,
                    "report_type": report_type,
                    "status": (
                        report.status.value if hasattr(report.status, "value") else str(report.status)
                    ),
                    "summary": summary_lines,
                },
            }
        )

    for history in histories:
        timeline_events.append(ClinicalHistoryService.build_timeline_event(history))

    timeline_events.sort(key=lambda item: _event_sort_key(item.get("event_date") or item.get("timestamp")))
    latest_event = max(
        timeline_events,
        key=lambda item: _event_sort_key(item.get("event_date") or item.get("timestamp")),
        default=None,
    )

    return {
        "success": True,
        "status": "ready" if timeline_events else "empty",
        "source": "db",
        "error": None,
        "data": timeline_events,
        "last_updated": (
            latest_event.get("event_date") or latest_event.get("timestamp")
            if latest_event
            else None
        ),
    }
