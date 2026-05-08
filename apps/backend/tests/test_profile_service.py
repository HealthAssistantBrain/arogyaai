from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.profile_service import ProfileService


def test_get_profile_bundle_returns_canonical_contract():
    user_id = uuid4()
    now = datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc)
    profile_updated_at = datetime(2026, 5, 8, 12, 30, tzinfo=timezone.utc)

    user = SimpleNamespace(
        id=user_id,
        email="patient@example.com",
        full_name="Patient Example",
        role="patient",
        is_email_verified=True,
        is_onboarding_done=False,
        onboarding_step=2,
        created_at=now,
        updated_at=now,
        medical_history=[],
        google_fit_connection=None,
    )
    profile = SimpleNamespace(
        supabase_id=user_id,
        email="patient@example.com",
        full_name="Patient Example",
        avatar_url=None,
        phone_number="+91-9999999999",
        date_of_birth=None,
        age=31,
        gender="female",
        occupation="Engineer",
        city="Kolkata",
        marital_status="single",
        height_cm=165,
        weight_kg=60,
        activity_level=8000,
        goals="Stay healthy",
        sleep_hours=7.5,
        stress_level=3,
        smoking=False,
        alcohol=False,
        appetite="normal",
        bowel_habits="normal",
        blood_group="O+",
        allergies="Dust",
        family_history="Diabetes",
        surgeries=None,
        hospitalizations=None,
        hospitalization_details=None,
        current_medications=None,
        updated_at=profile_updated_at,
    )

    db = MagicMock()

    with patch("services.profile_service.UserService.get_or_create_user_profile", return_value=profile), patch.object(
        ProfileService,
        "_serialize_wearable",
        return_value={"device_connections": {}, "google_fit": {}, "latest_metrics": {}, "ownership": {}},
    ), patch.object(
        ProfileService,
        "_serialize_settings",
        return_value={"auto_fetch_enabled": False, "fetch_interval_minutes": 15, "last_fetch_at": None, "ownership": {}},
    ), patch.object(
        ProfileService,
        "_serialize_preferences",
        return_value={"notifications": {"updated_at": None}, "ownership": {}},
    ), patch.object(
        ProfileService,
        "_serialize_health_baseline",
        return_value={"metrics": {}, "ownership": {}},
    ):
        result = ProfileService.get_profile_bundle(db, user)

    assert result["success"] is True
    assert result["status"] == "ready"
    assert result["source"] == "db"
    assert set(result["data"].keys()) == {
        "user",
        "profile",
        "onboarding",
        "medical_history",
        "wearable",
        "settings",
        "preferences",
        "health_baseline",
    }
    assert result["data"]["user"]["supabase_id"] == str(user_id)
    assert result["data"]["profile"]["phone_number"] == "+91-9999999999"
    assert result["data"]["onboarding"]["step"] == 2
    assert result["data"]["medical_history"]["ownership"]["conditions"] == "medical_history"
    assert result["last_updated"] == profile_updated_at.isoformat()
    db.refresh.assert_called_once_with(user)
