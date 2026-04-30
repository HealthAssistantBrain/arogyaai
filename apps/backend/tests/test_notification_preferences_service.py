from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import sys
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from models import NotificationTypeEnum
from services.notification_preferences_service import (
    NotificationPreferencesService,
    serialize_notification_preferences,
)


def test_serialize_notification_preferences_returns_expected_shape():
    preference_id = uuid4()
    user_id = uuid4()
    updated_at = "2026-04-30T11:00:00+00:00"
    preferences = SimpleNamespace(
        id=preference_id,
        user_id=user_id,
        email_enabled=True,
        push_enabled=False,
        ai_insights_email=True,
        ai_insights_push=False,
        health_alerts_email=True,
        health_alerts_push=True,
        reminders_email=False,
        reminders_push=True,
        updated_at=SimpleNamespace(isoformat=lambda: updated_at),
    )

    payload = serialize_notification_preferences(preferences)

    assert payload["id"] == str(preference_id)
    assert payload["user_id"] == str(user_id)
    assert payload["email_enabled"] is True
    assert payload["push_enabled"] is False
    assert payload["updated_at"] == updated_at


def test_update_preferences_merges_partial_payload():
    db = MagicMock()
    user = SimpleNamespace(id=uuid4())
    preferences = SimpleNamespace(
        id=uuid4(),
        user_id=user.id,
        email_enabled=True,
        push_enabled=True,
        ai_insights_email=True,
        ai_insights_push=True,
        health_alerts_email=True,
        health_alerts_push=True,
        reminders_email=True,
        reminders_push=True,
        updated_at=None,
    )

    with patch.object(NotificationPreferencesService, "get_or_create", return_value=preferences):
        NotificationPreferencesService.update_preferences(
            db,
            user,
            {"push_enabled": False, "reminders_email": False},
        )

    assert preferences.push_enabled is False
    assert preferences.reminders_email is False
    assert preferences.email_enabled is True
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(preferences)


def test_channel_enabled_respects_global_and_category_flags():
    preferences = SimpleNamespace(
        email_enabled=True,
        push_enabled=True,
        ai_insights_email=True,
        ai_insights_push=False,
        health_alerts_email=True,
        health_alerts_push=True,
        reminders_email=False,
        reminders_push=True,
    )

    assert NotificationPreferencesService.channel_enabled(preferences, NotificationTypeEnum.AI_INSIGHT, "email") is True
    assert NotificationPreferencesService.channel_enabled(preferences, NotificationTypeEnum.AI_INSIGHT, "push") is False
    assert NotificationPreferencesService.channel_enabled(preferences, NotificationTypeEnum.APPOINTMENT, "email") is False
    assert NotificationPreferencesService.channel_enabled(preferences, NotificationTypeEnum.HEALTH_ALERT, "push") is True
    assert NotificationPreferencesService.channel_enabled(preferences, NotificationTypeEnum.SIMULATION, "email") is True
