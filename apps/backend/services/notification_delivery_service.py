from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import logging
import uuid

from sqlalchemy.orm import Session

from database.session import SessionLocal
from models import Notification, NotificationDevice, User
from services.email_service import EmailService
from services.notification_preferences_service import NotificationPreferencesService
from services.push_service import PushService, PushSubscriptionExpiredError

logger = logging.getLogger("notification_delivery_service")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NotificationDeliveryService:
    @staticmethod
    def queue_notification(notification_id: str) -> dict[str, Any]:
        from workers.notification_tasks import send_notification_task

        task = send_notification_task.delay(notification_id)
        return {
            "task_id": getattr(task, "id", None),
            "state": getattr(task, "state", "QUEUED"),
        }

    @staticmethod
    def _notification_url(notification: Notification) -> str:
        metadata = notification.event_metadata if isinstance(notification.event_metadata, dict) else {}
        return str(metadata.get("url") or "/notifications")

    @staticmethod
    def _notification_subject(notification: Notification) -> str:
        return f"ArogyaAI: {notification.title}"

    @staticmethod
    def _notification_body(notification: Notification) -> str:
        metadata = notification.event_metadata if isinstance(notification.event_metadata, dict) else {}
        lines = [notification.description]
        if metadata.get("summary"):
            lines.append("")
            lines.append(str(metadata["summary"]))
        lines.append("")
        lines.append(f"Open in ArogyaAI: {NotificationDeliveryService._notification_url(notification)}")
        return "\n".join(lines)

    @staticmethod
    def _deliver_email(user: User, notification: Notification) -> dict[str, Any]:
        return EmailService.send_email(
            user.email,
            NotificationDeliveryService._notification_subject(notification),
            NotificationDeliveryService._notification_body(notification),
        )

    @staticmethod
    def _deliver_push(db: Session, devices: list[NotificationDevice], notification: Notification) -> tuple[int, int]:
        sent_count = 0
        expired_count = 0

        for device in devices:
            try:
                PushService.send_push(
                    device.subscription,
                    notification.title,
                    notification.description,
                    url=NotificationDeliveryService._notification_url(notification),
                    data={"notificationId": str(notification.id), "type": notification.notification_type.value},
                )
                sent_count += 1
            except PushSubscriptionExpiredError:
                expired_count += 1
                db.delete(device)
                logger.info(
                    "[Notifications] Removed expired push subscription device=%s notification=%s",
                    device.id,
                    notification.id,
                )
            except Exception as exc:
                logger.warning(
                    "[Notifications] Push delivery failed for notification=%s device=%s: %s",
                    notification.id,
                    device.id,
                    exc,
                )

        return sent_count, expired_count

    @staticmethod
    def deliver_notification(notification_id: str) -> dict[str, Any]:
        db = SessionLocal()
        try:
            try:
                notification_uuid = uuid.UUID(str(notification_id))
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid notification id") from exc

            notification = db.query(Notification).filter(Notification.id == notification_uuid).first()
            if notification is None:
                return {"status": "skipped", "reason": "missing_notification"}

            user = db.query(User).filter(User.id == notification.user_id, User.is_deleted == False).first()
            if user is None:
                notification.delivery_status = "failed"
                notification.last_delivery_error = "User not found for delivery."
                notification.processed_at = _utc_now()
                db.commit()
                return {"status": "skipped", "reason": "missing_user"}

            preferences = NotificationPreferencesService.get_or_create(db, user)
            push_devices = (
                db.query(NotificationDevice)
                .filter(NotificationDevice.user_id == user.id)
                .order_by(NotificationDevice.last_active.desc())
                .all()
            )

            email_permitted = bool(user.email) and NotificationPreferencesService.channel_enabled(
                preferences, notification.notification_type, "email"
            )
            push_permitted = bool(push_devices) and NotificationPreferencesService.channel_enabled(
                preferences, notification.notification_type, "push"
            )

            notification.delivery_attempts = int(notification.delivery_attempts or 0) + 1
            notification.processed_at = _utc_now()
            notification.last_delivery_error = None
            notification.email_status = "pending" if email_permitted else ("unavailable" if not user.email else "disabled")
            notification.push_status = "pending" if push_permitted else ("unsubscribed" if not push_devices else "disabled")
            db.commit()

            logger.info(
                "[Notifications] Processing notification=%s attempt=%s email=%s push=%s",
                notification.id,
                notification.delivery_attempts,
                email_permitted,
                push_permitted,
            )

            email_sent = False
            push_sent = 0
            errors: list[str] = []

            if email_permitted:
                try:
                    NotificationDeliveryService._deliver_email(user, notification)
                    email_sent = True
                    notification.email_status = "sent"
                except Exception as exc:
                    notification.email_status = "failed"
                    errors.append(f"email: {exc}")
                    logger.warning("[Notifications] Email delivery failed for notification=%s: %s", notification.id, exc)

            if push_permitted:
                push_sent, expired_count = NotificationDeliveryService._deliver_push(db, push_devices, notification)
                if push_sent > 0:
                    notification.push_status = "sent"
                elif expired_count == len(push_devices) and push_devices:
                    notification.push_status = "expired"
                    errors.append("push: all subscriptions expired")
                else:
                    notification.push_status = "failed"
                    errors.append("push: no deliveries succeeded")

            if email_sent or push_sent > 0 or (not email_permitted and not push_permitted):
                notification.delivery_status = "sent"
                notification.delivered_at = _utc_now()
            else:
                notification.delivery_status = "failed"
                notification.last_delivery_error = "; ".join(errors) or "Notification delivery failed."

            db.commit()
            db.refresh(notification)

            logger.info(
                "[Notifications] Delivery finished notification=%s status=%s email_status=%s push_status=%s",
                notification.id,
                notification.delivery_status,
                notification.email_status,
                notification.push_status,
            )

            if notification.delivery_status == "failed":
                raise RuntimeError(notification.last_delivery_error or "Notification delivery failed.")

            return {
                "status": notification.delivery_status,
                "notification_id": str(notification.id),
                "email_sent": email_sent,
                "push_sent": push_sent,
            }
        finally:
            db.close()
