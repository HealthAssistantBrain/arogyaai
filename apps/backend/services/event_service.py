"""
Event engine that converts system events into persisted notifications.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from database.session import SessionLocal
from models import NotificationTypeEnum, NotificationSeverityEnum, User
from services.notification_service import NotificationService

logger = logging.getLogger("event_service")

SUPPORTED_EVENTS = {
    "USER_LOGIN",
    "VITALS_UPDATED",
    "HEART_RATE_ALERT",
    "STEPS_MILESTONE",
    "SLEEP_ALERT",
    "DEVICE_CONNECTED",
}


def _coerce_payload(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return dict(payload)
    return {"value": payload}


def _coerce_metric_value(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key in payload and payload[key] is not None:
            try:
                return float(payload[key])
            except (TypeError, ValueError):
                continue
    return None


def emit_event(event_type: str, user_id: Any, payload: dict | Any | None = None) -> dict[str, Any] | None:
    normalized_event = str(event_type or "").strip().upper()
    if normalized_event not in SUPPORTED_EVENTS:
        logger.warning("[Events] Unsupported event type: %s", event_type)
        return None

    event_payload = _coerce_payload(payload)
    db = SessionLocal()
    try:
        user_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
        user = db.query(User).filter(User.id == user_uuid, User.is_deleted == False).first()
        if not user:
            logger.info("[Events] Skipping event=%s for missing user=%s", normalized_event, user_id)
            return None

        base_metadata = {
            "event_type": normalized_event,
            "payload": event_payload,
        }

        if normalized_event == "USER_LOGIN":
            return NotificationService.create_notification(
                db,
                user.id,
                NotificationTypeEnum.SYSTEM,
                "Login detected",
                "We detected a login to your ArogyaAI account.",
                NotificationSeverityEnum.INFO,
                metadata=base_metadata,
            )

        if normalized_event == "VITALS_UPDATED":
            return NotificationService.create_notification(
                db,
                user.id,
                NotificationTypeEnum.SYSTEM,
                "Vitals synced successfully",
                "Your latest health data was saved.",
                NotificationSeverityEnum.INFO,
                metadata=base_metadata,
            )

        if normalized_event == "DEVICE_CONNECTED":
            return NotificationService.create_notification(
                db,
                user.id,
                NotificationTypeEnum.SYSTEM,
                "Google Fit connected",
                "Your Google Fit account is connected.",
                NotificationSeverityEnum.INFO,
                metadata=base_metadata,
            )

        if normalized_event == "HEART_RATE_ALERT":
            heart_rate = _coerce_metric_value(event_payload, "heart_rate", "value", "bpm")
            if heart_rate is None or not (heart_rate > 110 or heart_rate < 45):
                return None
            return NotificationService.create_notification(
                db,
                user.id,
                NotificationTypeEnum.HEALTH_ALERT,
                "Heart rate alert",
                f"Heart rate is {heart_rate:g} bpm.",
                NotificationSeverityEnum.CRITICAL,
                metadata=base_metadata,
            )

        if normalized_event == "STEPS_MILESTONE":
            steps = _coerce_metric_value(event_payload, "steps", "value")
            if steps is None or steps <= 8000:
                return None
            return NotificationService.create_notification(
                db,
                user.id,
                NotificationTypeEnum.ACTIVITY,
                "Steps milestone reached",
                f"You reached {int(steps):,} steps.",
                NotificationSeverityEnum.INFO,
                metadata=base_metadata,
            )

        if normalized_event == "SLEEP_ALERT":
            sleep_hours = _coerce_metric_value(event_payload, "sleep", "value", "hours")
            if sleep_hours is None or sleep_hours >= 5:
                return None
            return NotificationService.create_notification(
                db,
                user.id,
                NotificationTypeEnum.HEALTH_ALERT,
                "Sleep alert",
                f"You slept for {sleep_hours:g} hours.",
                NotificationSeverityEnum.WARNING,
                metadata=base_metadata,
            )

        return None
    except Exception:
        logger.exception("[Events] Failed to emit event=%s for user=%s", normalized_event, user_id)
        return None
    finally:
        db.close()
