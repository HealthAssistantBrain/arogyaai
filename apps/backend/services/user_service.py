import uuid
from datetime import datetime, timezone, date
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


def _to_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _age_from_date_of_birth(dob: Optional[date]) -> Optional[int]:
    if dob is None:
        return None

    today = datetime.now(timezone.utc).date()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return max(years, 0)


def _activity_label(activity_level: Optional[int]) -> Optional[str]:
    if activity_level is None:
        return None
    if activity_level < 5000:
        return "Sedentary"
    if activity_level < 10000:
        return "Active"
    return "Very Active"


def _serialize_profile(user: User, profile: Optional[UserProfile]) -> dict:
    dob_value = profile.date_of_birth.isoformat() if profile and profile.date_of_birth else None
    derived_age = _age_from_date_of_birth(profile.date_of_birth) if profile else None
    activity_level = _to_int(profile.activity_level) if profile else None
    goals = profile.goals if profile and profile.goals else None
    return {
        "id": str(user.id),
        "user_id": str(user.id),
        "supabase_id": str(profile.supabase_id) if profile and profile.supabase_id else None,
        "email": user.email,
        "profile_email": profile.email if profile and profile.email else user.email,
        "full_name": profile.full_name if profile and profile.full_name else user.full_name,
        "avatar_url": profile.avatar_url if profile else None,
        "patient_id": None,
        "phone_number": profile.phone_number if profile else None,
        "phone": profile.phone_number if profile else None,
        "date_of_birth": dob_value,
        "dob": dob_value,
        "age": _to_int(profile.age) if profile and profile.age is not None else derived_age,
        "gender": profile.gender if profile else None,
        "height_cm": _to_float(profile.height_cm) if profile else None,
        "height": _to_float(profile.height_cm) if profile else None,
        "weight_kg": _to_float(profile.weight_kg) if profile else None,
        "weight": _to_float(profile.weight_kg) if profile else None,
        "activity_level": activity_level,
        "activity": _activity_label(activity_level),
        "goals": goals,
        "diet": goals,
        "blood_group": profile.blood_group if profile else None,
        "allergies": profile.allergies if profile else None,
        "is_email_verified": user.is_email_verified,
        "is_onboarding_done": user.is_onboarding_done,
        "onboarding_step": user.onboarding_step,
        "onboardingCompleted": user.is_onboarding_done,
        "onboardingStep": user.onboarding_step,
        "gmail_connected": bool(getattr(user, "gmail_connected", False)),
        "apple_connected": bool(getattr(user, "apple_connected", False)),
        "has_password": user.password_hash not in {"OAUTH_NO_PASSWORD", "SUPABASE_AUTH"},
        "role": "user",
        "created_at": profile.created_at.isoformat() if profile and profile.created_at else user.created_at.isoformat() if user.created_at else None,
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
            if profile.email != user.email:
                profile.email = user.email
                db.commit()
                db.refresh(profile)
            return profile

        profile = UserProfile(
            user_id=user.id,
            email=user.email,
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

        if "age" in updates:
            age_value = _to_int(updates.get("age"))
            if age_value is not None and not 0 <= age_value <= 130:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Age must be between 0 and 130",
                )
            profile.age = age_value

        if "height_cm" in updates or "height" in updates:
            height_value = _to_float(updates.get("height_cm", updates.get("height")))
            if height_value is not None and not 50 <= height_value <= 300:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Height must be between 50 and 300 cm",
                )
            profile.height_cm = height_value

        if "weight_kg" in updates or "weight" in updates:
            weight_value = _to_float(updates.get("weight_kg", updates.get("weight")))
            if weight_value is not None and not 20 <= weight_value <= 300:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Weight must be between 20 and 300 kg",
                )
            profile.weight_kg = weight_value

        if "activity_level" in updates:
            activity_level = _to_int(updates.get("activity_level"))
            if activity_level is not None and not 0 <= activity_level <= 50000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Activity level must be between 0 and 50000",
                )
            profile.activity_level = activity_level

        if "goals" in updates:
            goals = safe_input(updates.get("goals"), max_chars=4000)
            profile.goals = goals or None

        if "blood_group" in updates:
            blood_group_input = safe_input(updates.get("blood_group"), max_chars=10)
            blood_group = blood_group_input.upper() if blood_group_input else None
            profile.blood_group = blood_group or None

        if "allergies" in updates:
            allergies = safe_input(updates.get("allergies"), max_chars=4000)
            profile.allergies = allergies or None

        if profile.date_of_birth is not None:
            profile.age = _age_from_date_of_birth(profile.date_of_birth)

        if "is_onboarding_done" in updates:
            user.is_onboarding_done = bool(updates.get("is_onboarding_done"))

        if "onboarding_step" in updates:
            try:
                onboarding_step = int(updates.get("onboarding_step"))
            except (TypeError, ValueError):
                onboarding_step = user.onboarding_step
            user.onboarding_step = min(max(onboarding_step, 1), 6)

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
