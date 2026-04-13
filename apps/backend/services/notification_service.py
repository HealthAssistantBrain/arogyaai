"""
Notification service — persistence and read-state management.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import Notification, NotificationSeverityEnum, NotificationTypeEnum, User


def _serialize_notification(notification: Notification) -> dict:
    return {
        "id": str(notification.id),
        "user_id": str(notification.user_id),
        "type": notification.notification_type.value,
        "title": notification.title,
        "description": notification.description,
        "severity": notification.severity.value,
        "metadata": notification.event_metadata or {},
        "is_read": bool(notification.is_read),
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


def _notification_counts(db: Session, user: User) -> dict:
    base = db.query(Notification).filter(Notification.user_id == user.id)
    return {
        "all": base.count(),
        "unread": base.filter(Notification.is_read.is_(False)).count(),
        NotificationTypeEnum.AI_INSIGHT.value: base.filter(Notification.notification_type == NotificationTypeEnum.AI_INSIGHT).count(),
        NotificationTypeEnum.HEALTH_ALERT.value: base.filter(Notification.notification_type == NotificationTypeEnum.HEALTH_ALERT).count(),
        NotificationTypeEnum.APPOINTMENT.value: base.filter(Notification.notification_type == NotificationTypeEnum.APPOINTMENT).count(),
        NotificationTypeEnum.SYSTEM.value: base.filter(Notification.notification_type == NotificationTypeEnum.SYSTEM).count(),
        NotificationTypeEnum.ACTIVITY.value: base.filter(Notification.notification_type == NotificationTypeEnum.ACTIVITY).count(),
    }


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
    ) -> dict:
        try:
            notification_type_enum = notification_type if isinstance(notification_type, NotificationTypeEnum) else NotificationTypeEnum(str(notification_type).strip().lower())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification type") from exc

        try:
            severity_enum = severity if isinstance(severity, NotificationSeverityEnum) else NotificationSeverityEnum(str(severity).strip().lower())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification severity") from exc

        try:
            user_uuid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id") from exc

        now = datetime.now(timezone.utc)
        dedupe_window = now - timedelta(minutes=30)

        similar_notification = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_uuid,
                Notification.notification_type == notification_type_enum,
                Notification.title == title,
                Notification.created_at >= dedupe_window,
            )
            .order_by(Notification.created_at.desc())
            .first()
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

        notification = Notification(
            user_id=user_uuid,
            notification_type=notification_type_enum,
            title=title,
            description=description,
            severity=severity_enum,
            event_metadata=metadata or {},
        )
        db.add(notification)
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
            },
            "last_updated": notification.created_at.isoformat() if notification.created_at else None,
        }

    @staticmethod
    def list_notifications(
        db: Session,
        user: User,
        notification_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict:
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

        notifications = (
            query.order_by(Notification.created_at.desc())
            .all()
        )

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
    def get_unread_count(db: Session, user: User) -> dict:
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
    def mark_as_read(db: Session, user: User, notification_id: str) -> dict:
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
    def mark_all_as_read(db: Session, user: User) -> dict:
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
