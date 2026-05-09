from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from sqlalchemy.orm import Session

from models.clinical_history import ClinicalHistory
from models.generated_report import GeneratedReport
from models.lab_result import LabResult
from models.notification import Notification, NotificationTypeEnum
from models.report import Report
from models.timeline_event import TimelineEvent
from models.user_vital import UserVital, UserVitalTypeEnum
from services.clinical_history_service import ClinicalHistoryService
from services.timeline import build_report_event_payload

logger = logging.getLogger("uvicorn.error")


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


def _coerce_uuid(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _event_metadata(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _event_confidence_value(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def serialize_timeline_event(event: TimelineEvent) -> dict[str, Any]:
    metadata = _event_metadata(getattr(event, "event_metadata", None))
    event_type = str(getattr(event, "type", "") or "event")
    canonical_event_type = str(getattr(event, "event_type", "") or event_type or "event")
    normalized_type = event_type.strip().lower()
    timestamp = getattr(event, "timestamp", None)
    reference_id = getattr(event, "source_id", None) or getattr(event, "reference_id", None)
    summary = getattr(event, "summary", None) or metadata.get("summary")
    severity = getattr(event, "severity", None) or metadata.get("severity")
    confidence = _event_confidence_value(getattr(event, "confidence", None) or metadata.get("confidence"))

    payload = {
        "id": f"timeline_{event.id}",
        "type": event_type,
        "event_type": canonical_event_type,
        "source_type": getattr(event, "source_type", None) or metadata.get("source_type") or canonical_event_type,
        "source": metadata.get("source") or "timeline_events",
        "category": metadata.get("category") or ("report" if event_type == "report" else event_type),
        "title": getattr(event, "title", None) or metadata.get("title") or "Timeline event",
        "summary": summary,
        "description": metadata.get("description") or metadata.get("filename") or summary or "Clinical timeline event.",
        "timestamp": timestamp.isoformat() if timestamp else None,
        "event_date": timestamp.isoformat() if timestamp else None,
        "reference_id": str(reference_id) if reference_id else None,
        "source_id": str(reference_id) if reference_id else None,
        "severity": severity,
        "confidence": confidence,
        "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else None,
        "metadata": metadata,
    }

    if normalized_type == "report":
        filename = metadata.get("filename") or metadata.get("original_filename") or "Medical report"
        report_type = str(metadata.get("report_type") or "OTHER").replace("_", " ").title()
        status = str(metadata.get("status") or "UPLOADED").upper()
        payload.update(
            {
                "source": metadata.get("source") or "report upload",
                "category": "report",
                "title": metadata.get("title") or "Medical report uploaded",
                "description": metadata.get("description") or f"{filename} uploaded for clinical review.",
                "metrics": [
                    {"label": "File Name", "value": filename},
                    {"label": "Report Type", "value": report_type},
                    {"label": "Status", "value": status},
                ],
            }
        )
    elif normalized_type == "symptom analysis":
        risk_level = metadata.get("risk_level")
        urgency_level = metadata.get("urgency_level")
        payload.update(
            {
                "source": metadata.get("source") or "ai symptom analysis",
                "category": "symptom",
                "description": metadata.get("description") or summary or "AI symptom analysis saved.",
                "insights": summary,
                "possible_conditions": metadata.get("possible_causes") or [],
                "recommendations": metadata.get("recommendations") or [],
                "metrics": [
                    item
                    for item in [
                        {"label": "Severity", "value": severity} if severity else None,
                        {"label": "Risk", "value": risk_level} if risk_level else None,
                        {"label": "Urgency", "value": urgency_level} if urgency_level else None,
                        {"label": "Confidence", "value": f"{int(confidence * 100)}%"} if confidence is not None else None,
                    ]
                    if item is not None
                ],
            }
        )
    elif normalized_type == "ai report":
        payload.update(
            {
                "source": metadata.get("source") or "ai report generation",
                "category": "report_generation",
                "description": metadata.get("description") or summary or "AI-generated report saved.",
                "insights": summary,
                "recommendations": metadata.get("recommendations") or [],
                "metrics": [
                    item
                    for item in [
                        {"label": "Confidence", "value": f"{int(confidence * 100)}%"} if confidence is not None else None,
                    ]
                    if item is not None
                ],
            }
        )

    return payload


def create_timeline_event(db: Session, data: dict[str, Any], *, commit: bool = True) -> TimelineEvent:
    timestamp = data.get("timestamp") or datetime.now(timezone.utc)
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    user_id = _coerce_uuid(data.get("user_id"))
    reference_id = _coerce_uuid(data.get("source_id") or data.get("reference_id"))
    event_type = str(data.get("type") or "").strip()
    canonical_event_type = str(data.get("event_type") or event_type).strip()
    title = str(data.get("title") or "").strip()

    if user_id is None:
        raise ValueError("timeline event user_id is required")
    if not event_type:
        raise ValueError("timeline event type is required")
    if not title:
        raise ValueError("timeline event title is required")

    existing = None
    if reference_id is not None:
        existing = (
            db.query(TimelineEvent)
            .filter(
                TimelineEvent.user_id == user_id,
                TimelineEvent.type == event_type,
                TimelineEvent.reference_id == reference_id,
            )
            .first()
        )

    metadata = _event_metadata(data.get("metadata"))
    source_type = str(data.get("source_type") or "").strip() or None
    summary = str(data.get("summary") or "").strip() or None
    severity = str(data.get("severity") or "").strip() or None
    confidence = data.get("confidence")
    if existing:
        existing.title = title
        existing.event_type = canonical_event_type or existing.event_type
        existing.source_type = source_type or existing.source_type
        existing.summary = summary or existing.summary
        existing.severity = severity or existing.severity
        existing.confidence = confidence if confidence is not None else existing.confidence
        existing.timestamp = timestamp
        existing.source_id = reference_id or existing.source_id
        existing.event_metadata = {
            **_event_metadata(existing.event_metadata),
            **metadata,
        }
        if commit:
            db.commit()
        else:
            db.flush()
        db.refresh(existing)
        logger.info(
            "TIMELINE_EVENT_CREATED user_id=%s reference_id=%s timeline_event_id=%s type=%s",
            user_id,
            reference_id,
            existing.id,
            event_type,
        )
        return existing

    event = TimelineEvent(
        user_id=user_id,
        type=event_type,
        event_type=canonical_event_type or event_type,
        source_type=source_type,
        title=title,
        summary=summary,
        severity=severity,
        confidence=confidence,
        reference_id=reference_id,
        source_id=reference_id,
        timestamp=timestamp,
        event_metadata=metadata,
    )
    db.add(event)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(event)
    logger.info(
        "TIMELINE_EVENT_CREATED user_id=%s reference_id=%s timeline_event_id=%s type=%s",
        user_id,
        reference_id,
        event.id,
        event_type,
    )
    return event


def create_report_timeline_event(db: Session, report: Report, *, commit: bool = True) -> TimelineEvent:
    return create_timeline_event(db, build_report_event_payload(report), commit=commit)


def build_timeline_events(
    db: Session,
    user_id: Any,
    *,
    include_vitals: bool = True,
    limit_per_type: int = 30,
) -> list[dict[str, Any]]:
    vitals, labs, alerts, reports, histories, generated_reports, persisted_events = [], [], [], [], [], [], []

    try:
        persisted_events = (
            db.query(TimelineEvent)
            .filter(TimelineEvent.user_id == user_id)
            .order_by(TimelineEvent.timestamp.desc())
            .limit(max(limit_per_type, 60))
            .all()
        )
    except Exception as e:
        print(f"Error fetching timeline_events for timeline: {e}")

    if include_vitals:
        try:
            vitals = (
                db.query(UserVital)
                .filter(UserVital.user_id == user_id)
                .order_by(UserVital.timestamp.desc())
                .limit(max(limit_per_type, 60))
                .all()
            )
        except Exception as e:
            print(f"Error fetching user_vitals for timeline: {e}")

    try:
        labs = (
            db.query(LabResult)
            .filter(LabResult.user_id == user_id)
            .order_by(LabResult.timestamp.desc())
            .limit(limit_per_type)
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
            .limit(limit_per_type)
            .all()
        )
    except Exception as e:
        print(f"Error fetching alerts for timeline: {e}")

    try:
        reports = (
            db.query(Report)
            .filter(Report.user_id == user_id, Report.is_deleted == False)
            .order_by(Report.created_at.desc())
            .limit(limit_per_type)
            .all()
        )
    except Exception as e:
        print(f"Error fetching reports for timeline: {e}")

    try:
        histories = (
            db.query(ClinicalHistory)
            .filter(ClinicalHistory.user_id == user_id)
            .order_by(ClinicalHistory.created_at.desc())
            .limit(limit_per_type)
            .all()
        )
    except Exception as e:
        print(f"Error fetching clinical_history for timeline: {e}")

    try:
        generated_reports = (
            db.query(GeneratedReport)
            .filter(GeneratedReport.user_id == user_id)
            .order_by(GeneratedReport.created_at.desc())
            .limit(limit_per_type)
            .all()
        )
    except Exception as e:
        print(f"Error fetching generated_reports for timeline: {e}")

    timeline_events: list[dict[str, Any]] = []
    persisted_report_ids = set()

    for event in persisted_events:
        serialized_event = serialize_timeline_event(event)
        timeline_events.append(serialized_event)
        if serialized_event.get("type") == "report":
            report_id = serialized_event.get("reference_id") or serialized_event.get("metadata", {}).get("report_id")
            if report_id:
                persisted_report_ids.add(str(report_id))

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
                "metrics": [{"label": label, "value": f"{vital.value} {vital.unit or ''}".strip()}],
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
                "metrics": [{"label": "Severity", "value": severity_val.upper()}],
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
        if str(report.id) in persisted_report_ids:
            continue

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

    persisted_generated_ids = {
        serialized_event.get("reference_id")
        for serialized_event in timeline_events
        if str(serialized_event.get("type") or "").lower() == "ai report"
    }
    for generated_report in generated_reports:
        if str(generated_report.id) in persisted_generated_ids:
            continue

        payload = generated_report.report_payload if isinstance(generated_report.report_payload, dict) else {}
        sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
        first_section = sections[0] if sections else {}
        first_content = first_section.get("content", [None]) if isinstance(first_section, dict) else [None]
        summary = generated_report.summary or (first_content[0] if isinstance(first_content, list) else None)
        timeline_events.append(
            {
                "id": f"generated_report_{generated_report.id}",
                "type": "AI Report",
                "event_type": "generated_report",
                "source": "ai report generation",
                "source_type": "report_generation",
                "category": "report_generation",
                "title": generated_report.title,
                "summary": summary,
                "description": summary or "AI-generated report created.",
                "timestamp": generated_report.created_at.isoformat() if generated_report.created_at else None,
                "event_date": generated_report.created_at.isoformat() if generated_report.created_at else None,
                "reference_id": str(generated_report.id),
                "source_id": str(generated_report.id),
                "confidence": float(generated_report.confidence_score) if generated_report.confidence_score is not None else None,
                "recommendations": generated_report.recommendations if isinstance(generated_report.recommendations, list) else [],
                "metadata": {
                    "generated_report_id": str(generated_report.id),
                    "summary": summary,
                    "source": "ai report generation",
                    "url": "/report-generation",
                },
            }
        )

    timeline_events.sort(key=lambda item: _event_sort_key(item.get("event_date") or item.get("timestamp")))
    return timeline_events


def build_timeline_response(
    db: Session,
    user_id: Any,
    *,
    include_vitals: bool = True,
    limit_per_type: int = 30,
) -> dict[str, Any]:
    timeline_events = build_timeline_events(
        db,
        user_id,
        include_vitals=include_vitals,
        limit_per_type=limit_per_type,
    )
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
