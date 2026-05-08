from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models import BaselineMetricRecord, User, WearableMetric
from services.notification_preferences_service import (
    NotificationPreferencesService,
    serialize_notification_preferences,
)
from services.user_data_service import UserDataService
from services.user_service import (
    UserService,
    _age_from_date_of_birth,
    _serialize_device_connections,
    _serialize_initial_clinical_snapshot,
    _split_text_list,
    _to_float,
    _to_int,
)


class ProfileService:
    @staticmethod
    def _serialize_user(user: User, profile) -> dict[str, Any]:
        return {
            "id": str(user.id),
            "supabase_id": str(profile.supabase_id) if profile and profile.supabase_id else None,
            "email": user.email,
            "profile_email": profile.email if profile and profile.email else user.email,
            "full_name": profile.full_name if profile and profile.full_name else user.full_name,
            "avatar_url": profile.avatar_url if profile else None,
            "role": getattr(user, "role", "patient") or "patient",
            "is_email_verified": bool(user.is_email_verified),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    @staticmethod
    def _serialize_profile(profile) -> dict[str, Any]:
        if not profile:
            return {
                "full_name": None,
                "avatar_url": None,
                "phone_number": None,
                "date_of_birth": None,
                "age": None,
                "gender": None,
                "occupation": None,
                "city": None,
                "marital_status": None,
                "height_cm": None,
                "weight_kg": None,
                "activity_level": None,
                "goals": None,
                "sleep_hours": None,
                "stress_level": None,
                "smoking": None,
                "alcohol": None,
                "appetite": None,
                "bowel_habits": None,
                "blood_group": None,
                "updated_at": None,
            }

        derived_age = _age_from_date_of_birth(profile.date_of_birth)
        return {
            "full_name": profile.full_name,
            "avatar_url": profile.avatar_url,
            "phone_number": profile.phone_number,
            "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
            "age": _to_int(profile.age) if profile.age is not None else derived_age,
            "gender": profile.gender,
            "occupation": profile.occupation,
            "city": profile.city,
            "marital_status": profile.marital_status,
            "height_cm": _to_float(profile.height_cm),
            "weight_kg": _to_float(profile.weight_kg),
            "activity_level": _to_int(profile.activity_level),
            "goals": profile.goals,
            "sleep_hours": _to_float(profile.sleep_hours),
            "stress_level": _to_int(profile.stress_level),
            "smoking": profile.smoking,
            "alcohol": profile.alcohol,
            "appetite": profile.appetite,
            "bowel_habits": profile.bowel_habits,
            "blood_group": profile.blood_group,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }

    @staticmethod
    def _serialize_onboarding(user: User, profile) -> dict[str, Any]:
        return {
            "is_complete": bool(user.is_onboarding_done),
            "step": int(user.onboarding_step or 1),
            "is_email_verified": bool(user.is_email_verified),
            "initial_clinical_snapshot": _serialize_initial_clinical_snapshot(user),
            "source": {
                "state": "users.is_onboarding_done/onboarding_step",
                "snapshot": "clinical_history",
            },
        }

    @staticmethod
    def _serialize_medical_history(user: User, profile) -> dict[str, Any]:
        conditions = [
            row.condition_name
            for row in (getattr(user, "medical_history", []) or [])
            if getattr(row, "condition_name", None) and not bool(getattr(row, "is_deleted", False))
        ]
        return {
            "conditions": conditions,
            "allergies": _split_text_list(profile.allergies if profile else None),
            "family_history": _split_text_list(profile.family_history if profile else None),
            "surgeries": profile.surgeries if profile else None,
            "hospitalizations": profile.hospitalizations if profile else None,
            "hospitalization_details": profile.hospitalization_details if profile else None,
            "current_medications": profile.current_medications if profile else None,
            "ownership": {
                "conditions": "medical_history",
                "allergies": "user_profile.allergies",
                "family_history": "user_profile.family_history",
                "surgeries": "user_profile.surgeries",
                "hospitalizations": "user_profile.hospitalizations",
                "hospitalization_details": "user_profile.hospitalization_details",
                "current_medications": "user_profile.current_medications",
            },
        }

    @staticmethod
    def _serialize_latest_wearable_metrics(db: Session, user: User) -> dict[str, Any]:
        rows = (
            db.query(WearableMetric)
            .filter(WearableMetric.user_id == user.id)
            .order_by(WearableMetric.metric_type.asc(), WearableMetric.timestamp.desc())
            .all()
        )

        latest: dict[str, Any] = {}
        for row in rows:
            if row.metric_type in latest:
                continue
            latest[row.metric_type] = {
                "value": row.value,
                "unit": row.unit,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "source": row.source,
                "metadata": row.metric_metadata if isinstance(row.metric_metadata, dict) else {},
            }
        return latest

    @staticmethod
    def _serialize_wearable(db: Session, user: User) -> dict[str, Any]:
        connection = getattr(user, "google_fit_connection", None)
        return {
            "device_connections": _serialize_device_connections(user),
            "google_fit": {
                "email": getattr(connection, "google_email", None),
                "timezone": getattr(connection, "default_timezone", None),
                "last_synced_at": connection.last_synced_at.isoformat() if getattr(connection, "last_synced_at", None) else None,
                "last_sync_status": getattr(connection, "last_sync_status", None),
            },
            "latest_metrics": ProfileService._serialize_latest_wearable_metrics(db, user),
            "ownership": {
                "device_connections": "google_fit_connections + user_devices",
                "latest_metrics": "wearable_metrics",
            },
        }

    @staticmethod
    def _serialize_settings(db: Session, user: User) -> dict[str, Any]:
        setting = UserDataService.get_or_create_settings(db, user)
        return {
            "auto_fetch_enabled": bool(setting.auto_fetch_enabled),
            "fetch_interval_minutes": int(setting.fetch_interval_minutes),
            "last_fetch_at": setting.last_fetch_at.isoformat() if setting.last_fetch_at else None,
            "ownership": {
                "auto_fetch_enabled": "user_settings.auto_fetch_enabled",
                "fetch_interval_minutes": "user_settings.fetch_interval_minutes",
                "last_fetch_at": "user_settings.last_fetch_at",
            },
        }

    @staticmethod
    def _serialize_preferences(db: Session, user: User) -> dict[str, Any]:
        preferences = NotificationPreferencesService.get_or_create(db, user)
        return {
            "notifications": serialize_notification_preferences(preferences),
            "ownership": {
                "notifications": "notification_preferences",
            },
        }

    @staticmethod
    def _serialize_health_baseline(db: Session, user: User) -> dict[str, Any]:
        rows = (
            db.query(BaselineMetricRecord)
            .filter(BaselineMetricRecord.user_id == user.id)
            .order_by(BaselineMetricRecord.metric_name.asc())
            .all()
        )
        metrics = {}
        for row in rows:
            metrics[row.metric_name] = {
                "mean_7d": float(row.mean_7d) if row.mean_7d is not None else None,
                "mean_30d": float(row.mean_30d) if row.mean_30d is not None else None,
                "std_dev": float(row.std_dev) if row.std_dev is not None else None,
                "sample_count": int(row.sample_count or 0),
                "window_start": row.window_start.isoformat() if row.window_start else None,
                "window_end": row.window_end.isoformat() if row.window_end else None,
                "calculated_at": row.calculated_at.isoformat() if row.calculated_at else None,
                "metric_payload": row.metric_payload if isinstance(row.metric_payload, dict) else {},
            }
        return {
            "metrics": metrics,
            "ownership": {
                "metrics": "baseline_metrics",
            },
        }

    @staticmethod
    def _last_updated(*timestamps: str | None) -> str | None:
        ordered = [item for item in timestamps if item]
        return max(ordered) if ordered else None

    @staticmethod
    def get_profile_bundle(db: Session, user: User) -> dict[str, Any]:
        db.refresh(user)
        profile = UserService.get_or_create_user_profile(db, user)
        payload = {
            "user": ProfileService._serialize_user(user, profile),
            "profile": ProfileService._serialize_profile(profile),
            "onboarding": ProfileService._serialize_onboarding(user, profile),
            "medical_history": ProfileService._serialize_medical_history(user, profile),
            "wearable": ProfileService._serialize_wearable(db, user),
            "settings": ProfileService._serialize_settings(db, user),
            "preferences": ProfileService._serialize_preferences(db, user),
            "health_baseline": ProfileService._serialize_health_baseline(db, user),
        }
        last_updated = ProfileService._last_updated(
            payload["user"].get("updated_at"),
            payload["profile"].get("updated_at"),
            payload["settings"].get("last_fetch_at"),
            payload["preferences"]["notifications"].get("updated_at"),
        )
        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": payload,
            "last_updated": last_updated,
        }
