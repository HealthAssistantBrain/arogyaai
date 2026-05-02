"""
Notification service — event-triggered persistence, dispatch, and read-state management.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
import uuid
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database.session import SessionLocal
from models import (
    Alert,
    AlertTypeEnum,
    Notification,
    NotificationDevice,
    NotificationSeverityEnum,
    NotificationTypeEnum,
    SeverityEnum,
    User,
)
from services.notification_delivery_service import NotificationDeliveryService
from services.notification_preferences_service import NotificationPreferencesService

logger = logging.getLogger("notification_service")

EVENT_CONFIG: dict[str, dict[str, Any]] = {
    NotificationTypeEnum.AI_INSIGHT.value: {
        "notification_type": NotificationTypeEnum.AI_INSIGHT,
        "severity": NotificationSeverityEnum.INFO,
        "default_url": "/insights",
    },
    NotificationTypeEnum.HEALTH_ALERT.value: {
        "notification_type": NotificationTypeEnum.HEALTH_ALERT,
        "severity": NotificationSeverityEnum.WARNING,
        "default_url": "/lab-results",
    },
    NotificationTypeEnum.SIMULATION.value: {
        "notification_type": NotificationTypeEnum.SIMULATION,
        "severity": NotificationSeverityEnum.INFO,
        "default_url": "/simulator",
    },
    NotificationTypeEnum.APPOINTMENT.value: {
        "notification_type": NotificationTypeEnum.APPOINTMENT,
        "severity": NotificationSeverityEnum.INFO,
        "default_url": "/notifications",
    },
    NotificationTypeEnum.SYSTEM.value: {
        "notification_type": NotificationTypeEnum.SYSTEM,
        "severity": NotificationSeverityEnum.INFO,
        "default_url": "/notifications",
    },
    NotificationTypeEnum.ACTIVITY.value: {
        "notification_type": NotificationTypeEnum.ACTIVITY,
        "severity": NotificationSeverityEnum.INFO,
        "default_url": "/notifications",
    },
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_event_type(event_type: str) -> str:
    normalized = str(event_type or "").strip().lower()
    if normalized not in EVENT_CONFIG:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification event type")
    return normalized


def _coerce_user_uuid(user_id: Any) -> uuid.UUID:
    try:
        return user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id") from exc


def _coerce_severity(value: Any, fallback: NotificationSeverityEnum) -> NotificationSeverityEnum:
    if value is None:
        return fallback
    try:
        return value if isinstance(value, NotificationSeverityEnum) else NotificationSeverityEnum(str(value).strip().lower())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification severity") from exc


def _serialize_notification(notification: Notification) -> dict[str, Any]:
    return {
        "id": str(notification.id),
        "user_id": str(notification.user_id),
        "type": notification.notification_type.value,
        "title": notification.title,
        "description": notification.description,
        "severity": notification.severity.value,
        "metadata": notification.event_metadata or {},
        "is_read": bool(notification.is_read),
        "delivery_status": notification.delivery_status,
        "email_status": notification.email_status,
        "push_status": notification.push_status,
        "delivery_attempts": int(notification.delivery_attempts or 0),
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


def _serialize_dashboard_alert(alert: Alert) -> dict[str, Any]:
    return {
        "id": str(alert.id),
        "user_id": str(alert.user_id),
        "alert_type": alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type),
        "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
        "title": alert.title,
        "message": alert.message,
        "is_read": bool(alert.is_read),
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


def _notification_counts(db: Session, user: User) -> dict[str, int]:
    base = db.query(Notification).filter(Notification.user_id == user.id)
    return {
        "all": base.count(),
        "unread": base.filter(Notification.is_read.is_(False)).count(),
        NotificationTypeEnum.AI_INSIGHT.value: base.filter(Notification.notification_type == NotificationTypeEnum.AI_INSIGHT).count(),
        NotificationTypeEnum.HEALTH_ALERT.value: base.filter(Notification.notification_type == NotificationTypeEnum.HEALTH_ALERT).count(),
        NotificationTypeEnum.SIMULATION.value: base.filter(Notification.notification_type == NotificationTypeEnum.SIMULATION).count(),
        NotificationTypeEnum.APPOINTMENT.value: base.filter(Notification.notification_type == NotificationTypeEnum.APPOINTMENT).count(),
        NotificationTypeEnum.SYSTEM.value: base.filter(Notification.notification_type == NotificationTypeEnum.SYSTEM).count(),
        NotificationTypeEnum.ACTIVITY.value: base.filter(Notification.notification_type == NotificationTypeEnum.ACTIVITY).count(),
    }


def _dedupe_recent_notification(
    db: Session,
    *,
    user_id: uuid.UUID,
    notification_type: NotificationTypeEnum,
    title: str,
) -> Notification | None:
    dedupe_window = _utc_now() - timedelta(minutes=30)
    return (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.notification_type == notification_type,
            Notification.title == title,
            Notification.created_at >= dedupe_window,
        )
        .order_by(Notification.created_at.desc())
        .first()
    )


def _resolve_channel_status(
    *,
    channel_enabled: bool,
    channel_permitted: bool,
    is_available: bool,
    unavailable_status: str,
) -> str:
    if channel_enabled:
        return "pending"
    if channel_permitted and not is_available:
        return unavailable_status
    return "disabled"


def _store_dashboard_alert(
    *,
    user_id: uuid.UUID,
    title: str,
    message: str,
    severity: SeverityEnum,
    dedupe_minutes: int = 15,
) -> dict[str, Any]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
        if user is None:
            return {"created": False, "deduped": False, "reason": "missing_user"}

        threshold = _utc_now() - timedelta(minutes=dedupe_minutes)
        duplicate = (
            db.query(Alert)
            .filter(
                Alert.user_id == user_id,
                Alert.alert_type == AlertTypeEnum.VITAL_ANOMALY,
                Alert.severity == severity,
                Alert.title == title,
                Alert.created_at >= threshold,
            )
            .order_by(Alert.created_at.desc())
            .first()
        )
        if duplicate is not None:
            return {
                "created": False,
                "deduped": True,
                "alert": _serialize_dashboard_alert(duplicate),
            }

        alert = Alert(
            user_id=user_id,
            alert_type=AlertTypeEnum.VITAL_ANOMALY,
            severity=severity,
            title=title,
            message=message,
            is_read=False,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return {
            "created": True,
            "deduped": False,
            "alert": _serialize_dashboard_alert(alert),
        }
    finally:
        db.close()


class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        user_id,
        notification_type,
        title: str,
        description: str,
        severity,
        metadata: Optional[dict] = None,
        dispatch: bool = True,
    ) -> dict[str, Any]:
        try:
            notification_type_enum = notification_type if isinstance(notification_type, NotificationTypeEnum) else NotificationTypeEnum(str(notification_type).strip().lower())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification type") from exc

        severity_enum = _coerce_severity(severity, NotificationSeverityEnum.INFO)
        user_uuid = _coerce_user_uuid(user_id)

        similar_notification = _dedupe_recent_notification(
            db,
            user_id=user_uuid,
            notification_type=notification_type_enum,
            title=title,
        )
        if similar_notification:
            return {
                "success": True,
                "status": "ready",
                "source": "db",
                "error": None,
                "data": {
                    "notification": _serialize_notification(similar_notification),
                    "created": False,
                    "deduped": True,
                },
                "last_updated": similar_notification.created_at.isoformat() if similar_notification.created_at else None,
            }

        should_queue = bool(dispatch)
        now = _utc_now()
        notification = Notification(
            user_id=user_uuid,
            notification_type=notification_type_enum,
            title=title,
            description=description,
            severity=severity_enum,
            event_metadata=metadata or {},
            delivery_status="pending" if should_queue else "sent",
            email_status="pending" if should_queue else "disabled",
            push_status="pending" if should_queue else "disabled",
            queued_at=now if should_queue else None,
            delivered_at=now if not should_queue else None,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        delivery_job = None
        if should_queue:
            try:
                delivery_job = NotificationDeliveryService.queue_notification(str(notification.id))
            except Exception as exc:
                logger.exception("[Notifications] Failed to queue legacy notification id=%s: %s", notification.id, exc)
                notification.delivery_status = "failed"
                notification.last_delivery_error = str(exc)
                db.commit()
                db.refresh(notification)

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "notification": _serialize_notification(notification),
                "created": True,
                "deduped": False,
                "delivery_job": delivery_job,
            },
            "last_updated": notification.created_at.isoformat() if notification.created_at else None,
        }

    @staticmethod
    def list_notifications(
        db: Session,
        user: User,
        notification_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict[str, Any]:
        query = db.query(Notification).filter(Notification.user_id == user.id)

        if notification_type:
            normalized_type = notification_type.strip().lower()
            try:
                enum_value = NotificationTypeEnum(normalized_type)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid notification type",
                ) from exc
            query = query.filter(Notification.notification_type == enum_value)

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Notification.title.ilike(term),
                    Notification.description.ilike(term),
                )
            )

        notifications = query.order_by(Notification.created_at.desc()).all()
        counts = _notification_counts(db, user)
        unread_count = counts.get("unread", 0)

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "notifications": [_serialize_notification(notification) for notification in notifications],
                "counts": counts,
                "total_count": len(notifications),
                "unread_count": unread_count,
            },
            "last_updated": notifications[0].created_at.isoformat() if notifications else None,
        }

    @staticmethod
    def get_unread_count(db: Session, user: User) -> dict[str, Any]:
        counts = _notification_counts(db, user)
        unread_count = counts.get("unread", 0)

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "unread_count": unread_count,
            },
            "last_updated": None,
        }

    @staticmethod
    def mark_as_read(db: Session, user: User, notification_id: str) -> dict[str, Any]:
        try:
            notification_uuid = uuid.UUID(notification_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid notification id",
            ) from exc

        notification = (
            db.query(Notification)
            .filter(
                Notification.id == notification_uuid,
                Notification.user_id == user.id,
            )
            .first()
        )

        if not notification:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

        notification.is_read = True
        db.commit()
        db.refresh(notification)
        counts = _notification_counts(db, user)

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "notification": _serialize_notification(notification),
                "unread_count": counts.get("unread", 0),
            },
            "last_updated": notification.created_at.isoformat() if notification.created_at else None,
        }

    @staticmethod
    def mark_all_as_read(db: Session, user: User) -> dict[str, Any]:
        updated_count = (
            db.query(Notification)
            .filter(
                Notification.user_id == user.id,
                Notification.is_read.is_(False),
            )
            .update({Notification.is_read: True}, synchronize_session=False)
        )
        db.commit()
        counts = _notification_counts(db, user)

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "updated_count": updated_count,
                "unread_count": counts.get("unread", 0),
            },
            "last_updated": None,
        }


def _trigger_notification(
    *,
    user_id: str,
    event_type: str,
    title: str,
    message: str,
    data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    normalized_event_type = _normalize_event_type(event_type)
    user_uuid = _coerce_user_uuid(user_id)

    title = str(title or "").strip()
    message = str(message or "").strip()
    if not title or not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Notification title and message are required")

    config = EVENT_CONFIG[normalized_event_type]
    notification_type = config["notification_type"]
    severity = _coerce_severity((data or {}).get("severity"), config["severity"])
    payload = dict(data or {})
    payload.setdefault("url", config["default_url"])
    payload["event_type"] = normalized_event_type

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_uuid, User.is_deleted == False).first()
        if user is None:
            logger.info("[Notifications] Skipping event=%s for missing user=%s", normalized_event_type, user_id)
            return {
                "success": False,
                "status": "skipped",
                "source": "db",
                "error": None,
                "data": {"reason": "missing_user"},
                "last_updated": None,
            }

        similar_notification = _dedupe_recent_notification(
            db,
            user_id=user_uuid,
            notification_type=notification_type,
            title=title,
        )
        if similar_notification:
            logger.info(
                "[Notifications] Deduped event=%s user=%s notification=%s",
                normalized_event_type,
                user_uuid,
                similar_notification.id,
            )
            return {
                "success": True,
                "status": "ready",
                "source": "db",
                "error": None,
                "data": {
                    "notification": _serialize_notification(similar_notification),
                    "created": False,
                    "deduped": True,
                },
                "last_updated": similar_notification.created_at.isoformat() if similar_notification.created_at else None,
            }

        preferences = NotificationPreferencesService.get_or_create(db, user)
        push_device_exists = (
            db.query(NotificationDevice.id)
            .filter(NotificationDevice.user_id == user.id)
            .first()
            is not None
        )

        email_permitted = NotificationPreferencesService.channel_enabled(preferences, notification_type, "email")
        push_permitted = NotificationPreferencesService.channel_enabled(preferences, notification_type, "push")
        email_enabled = bool(user.email) and email_permitted
        push_enabled = push_device_exists and push_permitted

        now = _utc_now()
        payload["delivery"] = {
            "requested_channels": {
                "email": email_enabled,
                "push": push_enabled,
            },
        }

        notification = Notification(
            user_id=user.id,
            notification_type=notification_type,
            title=title,
            description=message,
            severity=severity,
            event_metadata=payload,
            delivery_status="pending" if (email_enabled or push_enabled) else "sent",
            email_status=_resolve_channel_status(
                channel_enabled=email_enabled,
                channel_permitted=email_permitted,
                is_available=bool(user.email),
                unavailable_status="unavailable",
            ),
            push_status=_resolve_channel_status(
                channel_enabled=push_enabled,
                channel_permitted=push_permitted,
                is_available=push_device_exists,
                unavailable_status="unsubscribed",
            ),
            queued_at=now if (email_enabled or push_enabled) else None,
            delivered_at=now if not (email_enabled or push_enabled) else None,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        logger.info(
            "[Notifications] Created notification id=%s user=%s event=%s email=%s push=%s",
            notification.id,
            user.id,
            normalized_event_type,
            email_enabled,
            push_enabled,
        )

        delivery_job = None
        if email_enabled or push_enabled:
            delivery_job = NotificationDeliveryService.queue_notification(str(notification.id))
            logger.info(
                "[Notifications] Queued delivery for notification=%s task=%s",
                notification.id,
                delivery_job.get("task_id"),
            )
        else:
            logger.info(
                "[Notifications] Stored notification=%s without external delivery because all channels were disabled or unavailable",
                notification.id,
            )

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "notification": _serialize_notification(notification),
                "created": True,
                "deduped": False,
                "delivery_job": delivery_job,
            },
            "last_updated": notification.created_at.isoformat() if notification.created_at else None,
        }
    finally:
        db.close()


def send_alert(
    user_id: str,
    alert: dict[str, Any],
    *,
    channels: tuple[str, ...] | list[str] | None = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Send an urgent health alert through the notification pipeline.

    Push and email delivery are queued through NotificationDeliveryService;
    the dashboard channel is persisted immediately as an Alert row.
    """
    user_uuid = _coerce_user_uuid(user_id)
    requested_channels = tuple(channels or ("push", "email", "dashboard"))
    channel_set = {str(channel).strip().lower() for channel in requested_channels if str(channel).strip()}

    alert_payload = dict(alert or {})
    level = str(alert_payload.get("level") or "CRITICAL").strip().upper()
    event = str(alert_payload.get("event") or "Emergency health event").strip()
    action = str(alert_payload.get("action") or "Seek immediate care").strip()
    confidence = alert_payload.get("confidence")

    severity = NotificationSeverityEnum.CRITICAL if level == "CRITICAL" else NotificationSeverityEnum.WARNING
    dashboard_severity = SeverityEnum.CRITICAL if severity == NotificationSeverityEnum.CRITICAL else SeverityEnum.WARNING
    title_prefix = "Emergency" if severity == NotificationSeverityEnum.CRITICAL else "Health alert"
    title = f"{title_prefix}: {event}"
    message = f"{event}. {action}."

    payload = {
        **(metadata or {}),
        "emergency": severity == NotificationSeverityEnum.CRITICAL,
        "system_alert": True,
        "level": level,
        "event": event,
        "confidence": confidence,
        "action": action,
        "channels": sorted(channel_set),
        "severity": severity.value,
        "url": "/dashboard",
    }

    notification_result = None
    if channel_set.intersection({"push", "email"}):
        notification_result = _trigger_notification(
            user_id=str(user_uuid),
            event_type=NotificationTypeEnum.HEALTH_ALERT.value,
            title=title,
            message=message,
            data=payload,
        )

    dashboard_result = None
    if "dashboard" in channel_set:
        dashboard_result = _store_dashboard_alert(
            user_id=user_uuid,
            title=title,
            message=message,
            severity=dashboard_severity,
            dedupe_minutes=int(payload.get("rate_limit_minutes") or 15),
        )

    logger.info(
        "[Notifications] Emergency alert requested user=%s level=%s channels=%s notification=%s dashboard=%s",
        user_uuid,
        level,
        sorted(channel_set),
        bool(notification_result),
        bool(dashboard_result),
    )

    return {
        "success": True,
        "status": "ready",
        "source": "notification_service",
        "error": None,
        "data": {
            "alert": alert_payload,
            "channels": sorted(channel_set),
            "notification": notification_result,
            "dashboard_alert": dashboard_result,
        },
        "last_updated": _utc_now().isoformat(),
    }


async def send_alert_async(
    user_id: str,
    alert: dict[str, Any],
    *,
    channels: tuple[str, ...] | list[str] | None = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        send_alert,
        user_id,
        alert,
        channels=channels,
        metadata=metadata,
    )


def trigger_notification_sync(
    user_id: str,
    event_type: str,
    title: str,
    message: str,
    data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    logger.info("[Notifications] Event triggered user=%s event=%s", user_id, event_type)
    return _trigger_notification(
        user_id=user_id,
        event_type=event_type,
        title=title,
        message=message,
        data=data,
    )


async def trigger_notification(
    user_id: str,
    event_type: str,
    title: str,
    message: str,
    data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        trigger_notification_sync,
        user_id,
        event_type,
        title,
        message,
        data,
    )
