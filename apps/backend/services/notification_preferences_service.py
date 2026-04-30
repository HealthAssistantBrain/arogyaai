from __future__ import annotations

from typing import Any

from models import NotificationPreference, NotificationTypeEnum, User


PREFERENCE_FIELDS = {
    "email_enabled",
    "push_enabled",
    "ai_insights_email",
    "ai_insights_push",
    "health_alerts_email",
    "health_alerts_push",
    "reminders_email",
    "reminders_push",
}


NOTIFICATION_CATEGORY_MAP = {
    NotificationTypeEnum.AI_INSIGHT: "ai_insights",
    NotificationTypeEnum.SIMULATION: "ai_insights",
    NotificationTypeEnum.HEALTH_ALERT: "health_alerts",
    NotificationTypeEnum.APPOINTMENT: "reminders",
}


def serialize_notification_preferences(preferences: NotificationPreference) -> dict[str, Any]:
    return {
        "id": str(preferences.id),
        "user_id": str(preferences.user_id),
        "email_enabled": bool(preferences.email_enabled),
        "push_enabled": bool(preferences.push_enabled),
        "ai_insights_email": bool(preferences.ai_insights_email),
        "ai_insights_push": bool(preferences.ai_insights_push),
        "health_alerts_email": bool(preferences.health_alerts_email),
        "health_alerts_push": bool(preferences.health_alerts_push),
        "reminders_email": bool(preferences.reminders_email),
        "reminders_push": bool(preferences.reminders_push),
        "updated_at": preferences.updated_at.isoformat() if preferences.updated_at else None,
    }


class NotificationPreferencesService:
    @staticmethod
    def get_or_create(db, user: User) -> NotificationPreference:
        preferences = (
            db.query(NotificationPreference)
            .filter(NotificationPreference.user_id == user.id)
            .first()
        )
        if preferences:
            return preferences

        preferences = NotificationPreference(user_id=user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
        return preferences

    @staticmethod
    def get_preferences(db, user: User) -> dict[str, Any]:
        preferences = NotificationPreferencesService.get_or_create(db, user)
        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": serialize_notification_preferences(preferences),
            "last_updated": preferences.updated_at.isoformat() if preferences.updated_at else None,
        }

    @staticmethod
    def update_preferences(db, user: User, payload: dict[str, Any]) -> dict[str, Any]:
        preferences = NotificationPreferencesService.get_or_create(db, user)

        for key, value in (payload or {}).items():
            if key not in PREFERENCE_FIELDS or value is None:
                continue
            setattr(preferences, key, bool(value))

        db.commit()
        db.refresh(preferences)

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": serialize_notification_preferences(preferences),
            "last_updated": preferences.updated_at.isoformat() if preferences.updated_at else None,
        }

    @staticmethod
    def channel_enabled(
        preferences: NotificationPreference,
        notification_type: NotificationTypeEnum,
        channel: str,
    ) -> bool:
        normalized_channel = str(channel or "").strip().lower()
        if normalized_channel not in {"email", "push"}:
            return False

        global_field = f"{normalized_channel}_enabled"
        if not bool(getattr(preferences, global_field, False)):
            return False

        category = NOTIFICATION_CATEGORY_MAP.get(notification_type)
        if not category:
            return False

        category_field = f"{category}_{normalized_channel}"
        return bool(getattr(preferences, category_field, False))

    @staticmethod
    def category_for(notification_type: NotificationTypeEnum) -> str | None:
        return NOTIFICATION_CATEGORY_MAP.get(notification_type)
