import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from core.utils import safe_input
from models import User, UserProfile, Session as DBSession


def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _serialize_profile(user: User, profile: Optional[UserProfile]) -> dict:
    dob_value = profile.date_of_birth.isoformat() if profile and profile.date_of_birth else None
    return {
        "id": str(user.id),
        "user_id": str(user.id),
        "email": user.email,
        "full_name": profile.full_name if profile and profile.full_name else user.full_name,
        "avatar_url": profile.avatar_url if profile else None,
        "patient_id": None,
        "phone_number": profile.phone_number if profile else None,
        "phone": profile.phone_number if profile else None,
        "date_of_birth": dob_value,
        "dob": dob_value,
        "gender": profile.gender if profile else None,
        "height_cm": _to_float(profile.height_cm) if profile else None,
        "height": _to_float(profile.height_cm) if profile else None,
        "weight_kg": _to_float(profile.weight_kg) if profile else None,
        "weight": _to_float(profile.weight_kg) if profile else None,
        "blood_group": profile.blood_group if profile else None,
        "allergies": profile.allergies if profile else None,
        "is_email_verified": user.is_email_verified,
        "is_onboarding_done": user.is_onboarding_done,
        "onboarding_step": user.onboarding_step,
        "gmail_connected": bool(getattr(user, "gmail_connected", False)),
        "apple_connected": bool(getattr(user, "apple_connected", False)),
        "has_password": user.password_hash != "OAUTH_NO_PASSWORD",
        "role": "user",
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": (
            profile.updated_at.isoformat() if profile and profile.updated_at else user.updated_at.isoformat() if user.updated_at else None
        ),
    }


def _profile_response(user: User, profile: Optional[UserProfile]) -> dict:
    payload = _serialize_profile(user, profile)
    return {
        "success": True,
        "status": "ready",
        "source": "db",
        "error": None,
        "data": payload,
        "last_updated": payload.get("updated_at") or payload.get("created_at"),
    }

class UserService:
    @staticmethod
    def get_or_create_user_profile(db: Session, user: User) -> UserProfile:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if profile:
            return profile

        profile = UserProfile(
            user_id=user.id,
            full_name=user.full_name,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_user_me(db: Session, user: User) -> dict:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        return {
            "success": True,
            "status": "ready",
            "error": None,
            "data": {
                **_serialize_profile(user, profile),
                "health_score": float(user.health_score) if user.health_score is not None else 0.0,
                "score_change": float(user.score_change_percent) if user.score_change_percent is not None else 0.0,
            },
        }

    @staticmethod
    def update_user_me(db: Session, user: User, updates: dict) -> dict:
        allowed_fields = {"full_name", "is_onboarding_done", "onboarding_step"}
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(user, field, value)
        
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        
        return {
            "success": True,
            "status": "ready",
            "error": None,
            "data": {
                "message": "Profile updated",
                "id": str(user.id),
                "user": {
                    "is_onboarding_done": user.is_onboarding_done,
                    "onboarding_step": user.onboarding_step
                }
            }
        }

    @staticmethod
    def get_user_profile(db: Session, user: User) -> dict:
        profile = UserService.get_or_create_user_profile(db, user)
        return _profile_response(user, profile)

    @staticmethod
    def update_user_profile(db: Session, user: User, updates: dict) -> dict:
        profile = UserService.get_or_create_user_profile(db, user)

        if "full_name" in updates:
            full_name = safe_input(updates.get("full_name"))
            profile.full_name = full_name or None
            user.full_name = full_name or None

        if "avatar_url" in updates:
            avatar_url = safe_input(updates.get("avatar_url"), max_chars=4000)
            profile.avatar_url = avatar_url or None

        phone_value = updates.get("phone_number", updates.get("phone"))
        if phone_value is not None:
            phone = safe_input(phone_value, max_chars=20)
            profile.phone_number = phone or None

        dob_value = updates.get("date_of_birth", updates.get("dob"))
        if dob_value is not None:
            dob_str = safe_input(dob_value, max_chars=20)
            if dob_str:
                try:
                    profile.date_of_birth = datetime.strptime(dob_str, "%Y-%m-%d").date()
                except ValueError:
                    pass
            else:
                profile.date_of_birth = None

        if "gender" in updates:
            gender = safe_input(updates.get("gender"), max_chars=20)
            profile.gender = gender or None

        if "height_cm" in updates or "height" in updates:
            profile.height_cm = _to_float(updates.get("height_cm", updates.get("height")))

        if "weight_kg" in updates or "weight" in updates:
            profile.weight_kg = _to_float(updates.get("weight_kg", updates.get("weight")))

        if "blood_group" in updates:
            blood_group = safe_input(updates.get("blood_group"), max_chars=10).upper()
            profile.blood_group = blood_group or None

        if "allergies" in updates:
            allergies = safe_input(updates.get("allergies"), max_chars=4000)
            profile.allergies = allergies or None

        profile.updated_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        db.refresh(profile)

        return _profile_response(user, profile)

    @staticmethod
    def delete_user_me(db: Session, user: User) -> dict:
        # 1. Soft-delete user
        user.is_deleted = True
        user.updated_at = datetime.now(timezone.utc)
        
        # 2. Revoke all active sessions
        db.query(DBSession).filter(
            DBSession.user_id == user.id,
            DBSession.is_revoked == False
        ).update({"is_revoked": True}, synchronize_session='fetch')

        db.commit()
        return {"success": True, "status": "ready", "error": None, "data": {"message": "Account deactivated"}}
