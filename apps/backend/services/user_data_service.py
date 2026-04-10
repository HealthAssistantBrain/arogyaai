"""
User data service — canonical profile, settings, onboarding, and vitals storage.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.utils import safe_input
from models import (
    User,
    UserProfile,
    UserSetting,
    UserVital,
    UserVitalSourceEnum,
    UserVitalTypeEnum,
)
from services.user_service import UserService

ALLOWED_FETCH_INTERVALS = {5, 10, 15, 20, 25, 30}
RANGE_WINDOWS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, (int, float)):
        # Accept either epoch seconds or epoch milliseconds.
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1000.0
        return datetime.fromtimestamp(seconds, tz=timezone.utc)

    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timestamp format") from exc

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timestamp value")


def _serialize_setting(setting: UserSetting, user_id: str) -> dict:
    return {
        "id": str(setting.id),
        "user_id": user_id,
        "auto_fetch_enabled": bool(setting.auto_fetch_enabled),
        "fetch_interval_minutes": int(setting.fetch_interval_minutes),
        "last_fetch_at": setting.last_fetch_at.isoformat() if setting.last_fetch_at else None,
    }


def _serialize_vital(vital: UserVital) -> dict:
    return {
        "id": str(vital.id),
        "user_id": str(vital.user_id),
        "type": vital.vital_type.value,
        "value": float(vital.value),
        "unit": vital.unit,
        "timestamp": vital.timestamp.isoformat() if vital.timestamp else None,
        "source": vital.source.value,
        "created_at": vital.created_at.isoformat() if vital.created_at else None,
    }


class UserDataService:
    @staticmethod
    def get_or_create_profile(db: Session, user: User) -> UserProfile:
        return UserService.get_or_create_user_profile(db, user)

    @staticmethod
    def get_or_create_settings(db: Session, user: User) -> UserSetting:
        setting = db.query(UserSetting).filter(UserSetting.user_id == user.id).first()
        if setting:
            return setting

        setting = UserSetting(
            user_id=user.id,
            auto_fetch_enabled=False,
            fetch_interval_minutes=15,
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
        return setting

    @staticmethod
    def get_profile(db: Session, user: User) -> dict:
        return UserService.get_user_profile(db, user)

    @staticmethod
    def update_profile(db: Session, user: User, updates: dict) -> dict:
        normalized = dict(updates or {})
        if "date_of_birth" not in normalized and "dob" in normalized:
            normalized["date_of_birth"] = normalized["dob"]
        if "phone_number" not in normalized and "phone" in normalized:
            normalized["phone_number"] = normalized["phone"]
        if "height_cm" not in normalized and "height" in normalized:
            normalized["height_cm"] = normalized["height"]
        if "weight_kg" not in normalized and "weight" in normalized:
            normalized["weight_kg"] = normalized["weight"]

        payload = {}
        if "full_name" in normalized:
            payload["full_name"] = safe_input(normalized.get("full_name"))
        if "avatar_url" in normalized:
            payload["avatar_url"] = normalized.get("avatar_url")
        if "phone_number" in normalized:
            payload["phone_number"] = normalized.get("phone_number")
        if "date_of_birth" in normalized:
            payload["date_of_birth"] = normalized.get("date_of_birth")
        if "gender" in normalized:
            payload["gender"] = normalized.get("gender")
        if "height_cm" in normalized:
            payload["height_cm"] = normalized.get("height_cm")
        if "weight_kg" in normalized:
            payload["weight_kg"] = normalized.get("weight_kg")
        if "blood_group" in normalized:
            payload["blood_group"] = normalized.get("blood_group")
        if "allergies" in normalized:
            payload["allergies"] = normalized.get("allergies")
        return UserService.update_user_profile(db, user, payload)

    @staticmethod
    def save_onboarding(db: Session, user: User, payload: dict) -> dict:
        normalized = dict(payload or {})
        if "date_of_birth" not in normalized and "dob" in normalized:
            normalized["date_of_birth"] = normalized["dob"]
        if "phone_number" not in normalized and "phone" in normalized:
            normalized["phone_number"] = normalized["phone"]
        if "height_cm" not in normalized and "height" in normalized:
            normalized["height_cm"] = normalized["height"]
        if "weight_kg" not in normalized and "weight" in normalized:
            normalized["weight_kg"] = normalized["weight"]

        profile_payload = {
            key: normalized.get(key)
            for key in ("full_name", "date_of_birth", "gender", "phone_number", "height_cm", "weight_kg", "blood_group", "allergies")
            if key in normalized and normalized.get(key) is not None
        }
        result = UserDataService.update_profile(db, user, profile_payload)

        user_updates = {}
        if normalized.get("is_onboarding_done") is not None:
            user_updates["is_onboarding_done"] = bool(normalized.get("is_onboarding_done"))
        if normalized.get("onboarding_step") is not None:
            user_updates["onboarding_step"] = int(normalized.get("onboarding_step"))

        if user_updates:
            UserService.update_user_me(db, user, user_updates)

        return result

    @staticmethod
    def get_settings(db: Session, user: User) -> dict:
        setting = UserDataService.get_or_create_settings(db, user)
        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": _serialize_setting(setting, str(user.id)),
            "last_updated": setting.last_fetch_at.isoformat() if setting.last_fetch_at else None,
        }

    @staticmethod
    def update_settings(db: Session, user: User, payload: dict) -> dict:
        setting = UserDataService.get_or_create_settings(db, user)

        auto_fetch_enabled = payload.get("auto_fetch_enabled")
        fetch_interval_minutes = payload.get("fetch_interval_minutes")

        if auto_fetch_enabled is None or fetch_interval_minutes is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="auto_fetch_enabled and fetch_interval_minutes are required",
            )

        interval = int(fetch_interval_minutes)
        if interval not in ALLOWED_FETCH_INTERVALS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fetch_interval_minutes must be one of [5, 10, 15, 20, 25, 30]",
            )

        setting.auto_fetch_enabled = bool(auto_fetch_enabled)
        setting.fetch_interval_minutes = interval
        db.commit()
        db.refresh(setting)

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": _serialize_setting(setting, str(user.id)),
            "last_updated": setting.last_fetch_at.isoformat() if setting.last_fetch_at else None,
        }

    @staticmethod
    def list_vitals(
        db: Session,
        user: User,
        vital_type: Optional[str] = None,
        range_value: str = "24h",
    ) -> dict:
        query = db.query(UserVital).filter(UserVital.user_id == user.id)

        if vital_type:
            try:
                enum_value = UserVitalTypeEnum(vital_type.strip().lower())
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vital type") from exc
            query = query.filter(UserVital.vital_type == enum_value)

        if range_value and range_value != "all":
            window = RANGE_WINDOWS.get(range_value)
            if window is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid range value")
            query = query.filter(UserVital.timestamp >= _now_utc() - window)

        vitals = query.order_by(UserVital.timestamp.asc()).all()
        payload = [_serialize_vital(vital) for vital in vitals]

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "vitals": payload,
                "total_count": len(payload),
                "type": vital_type,
                "range": range_value,
            },
            "last_updated": payload[-1]["timestamp"] if payload else None,
        }

    @staticmethod
    def store_vitals(
        db: Session,
        user: User,
        records: Iterable[dict],
    ) -> list[UserVital]:
        saved: list[UserVital] = []

        for record in records:
            vital_type = record.get("type")
            if not vital_type:
                continue

            try:
                vital_enum = UserVitalTypeEnum(str(vital_type).strip().lower())
            except ValueError:
                continue

            try:
                source_enum = UserVitalSourceEnum(str(record.get("source") or "google_fit").strip().lower())
            except ValueError:
                source_enum = UserVitalSourceEnum.GOOGLE_FIT

            timestamp = _parse_timestamp(record.get("timestamp"))
            value_raw = record.get("value")
            if value_raw is None:
                continue
            try:
                value = float(value_raw)
            except (TypeError, ValueError):
                continue
            if value == 0 and vital_enum != UserVitalTypeEnum.STEPS:
                continue
            unit = str(record.get("unit") or "")
            if not unit:
                continue

            existing = (
                db.query(UserVital)
                .filter(
                    UserVital.user_id == user.id,
                    UserVital.vital_type == vital_enum,
                    UserVital.timestamp == timestamp,
                    UserVital.source == source_enum,
                )
                .first()
            )

            if existing:
                existing.value = value
                existing.unit = unit
                vital = existing
            else:
                vital = UserVital(
                    user_id=user.id,
                    vital_type=vital_enum,
                    value=value,
                    unit=unit,
                    timestamp=timestamp,
                    source=source_enum,
                )
                db.add(vital)
            saved.append(vital)

        if saved:
            db.commit()
            for item in saved:
                db.refresh(item)

        return saved

    @staticmethod
    def touch_settings_fetch(db: Session, user: User) -> None:
        setting = UserDataService.get_or_create_settings(db, user)
        setting.last_fetch_at = _now_utc()
        db.commit()
