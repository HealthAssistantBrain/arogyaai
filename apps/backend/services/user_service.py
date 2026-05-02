import uuid
from datetime import datetime, timezone, date
from typing import Optional, Any

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from core.utils import safe_input
from models import User, UserDeviceProviderEnum, UserProfile, Session as DBSession
from models.user import ROLE_PATIENT


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


def _clean_text(value: Any, max_chars: int = 4000) -> Optional[str]:
    text = safe_input(value, max_chars=max_chars)
    return text or None


def _split_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    else:
        items = []

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def _join_text_list(value: Any) -> Optional[str]:
    items = _split_text_list(value)
    return ", ".join(items) if items else None


def _to_bool(value: Any) -> Optional[bool]:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)

    normalized = str(value).strip().lower()
    if normalized in {"yes", "true", "1", "y"}:
        return True
    if normalized in {"no", "false", "0", "n"}:
        return False
    return None


def _yes_no_label(value: Optional[bool]) -> Optional[str]:
    if value is None:
        return None
    return "yes" if value else "no"


def _parse_duration(value: Any) -> tuple[Optional[int], Optional[str]]:
    text = str(value or "").strip()
    if not text:
        return None, None

    parts = text.split()
    try:
        duration_value = int(parts[0]) if parts else None
    except (TypeError, ValueError):
        duration_value = None

    duration_unit = parts[1].lower() if len(parts) > 1 else None
    if duration_unit and duration_unit.endswith("s"):
        duration_unit = duration_unit[:-1]
    if duration_unit not in {"hour", "day", "week"}:
        duration_unit = None

    return duration_value, duration_unit


def _serialize_device_connections(user: User) -> dict[str, bool]:
    google_fit_connection = getattr(user, "google_fit_connection", None)
    user_devices = list(getattr(user, "user_devices", []) or [])

    def _device_connected(provider: UserDeviceProviderEnum) -> bool:
        return any(
            getattr(device, "provider", None) == provider and bool(getattr(device, "is_active", False))
            for device in user_devices
        )

    google_fit_connected = bool(
        getattr(google_fit_connection, "access_token_encrypted", None)
        or getattr(google_fit_connection, "refresh_token_encrypted", None)
    ) or _device_connected(UserDeviceProviderEnum.GOOGLE_FIT)

    return {
        "google_fit_connected": google_fit_connected,
        "apple_health_connected": _device_connected(UserDeviceProviderEnum.APPLE_HEALTH),
        "fitbit_connected": _device_connected(UserDeviceProviderEnum.FITBIT),
    }


def _serialize_initial_clinical_snapshot(user: User) -> dict[str, Any]:
    histories = list(getattr(user, "clinical_histories", []) or [])
    latest_history = max(
        histories,
        key=lambda item: item.created_at or datetime.min.replace(tzinfo=timezone.utc),
        default=None,
    )
    if latest_history is None:
        return {
            "chief_complaint": None,
            "symptoms": [],
            "duration": None,
            "duration_value": None,
            "duration_unit": None,
            "onset": None,
            "severity": None,
        }

    duration_value, duration_unit = _parse_duration(getattr(latest_history, "duration", None))
    return {
        "chief_complaint": _clean_text(getattr(latest_history, "chief_complaint", None)),
        "symptoms": _split_text_list(getattr(latest_history, "associated_symptoms", []) or []),
        "duration": _clean_text(getattr(latest_history, "duration", None)),
        "duration_value": duration_value,
        "duration_unit": duration_unit,
        "onset": _clean_text(getattr(latest_history, "onset", None), max_chars=50),
        "severity": _to_int(getattr(latest_history, "severity", None)),
    }


def _serialize_structured_sections(user: User, profile: Optional[UserProfile]) -> dict[str, Any]:
    conditions = [
        row.condition_name
        for row in (getattr(user, "medical_history", []) or [])
        if getattr(row, "condition_name", None) and not bool(getattr(row, "is_deleted", False))
    ]
    allergies = _split_text_list(profile.allergies if profile else None)
    family_history = _split_text_list(profile.family_history if profile else None)
    device_connections = _serialize_device_connections(user)
    initial_snapshot = _serialize_initial_clinical_snapshot(user)

    return {
        "user_profile": {
            "name": profile.full_name if profile and profile.full_name else user.full_name,
            "age": _to_int(profile.age) if profile and profile.age is not None else _age_from_date_of_birth(profile.date_of_birth) if profile else None,
            "sex": profile.gender if profile else None,
            "occupation": profile.occupation if profile else None,
            "city": profile.city if profile else None,
            "marital_status": profile.marital_status if profile else None,
        },
        "medical_history": {
            "conditions": conditions,
            "allergies": allergies,
            "family_history": family_history,
            "surgeries": profile.surgeries if profile else None,
            "hospitalizations": _to_bool(profile.hospitalizations) if profile else None,
            "hospitalization_details": profile.hospitalization_details if profile else None,
            "medications": profile.current_medications if profile else None,
        },
        "lifestyle_profile": {
            "activity_level": _to_int(profile.activity_level) if profile else None,
            "diet": _split_text_list(profile.goals if profile else None),
            "sleep_hours": _to_float(profile.sleep_hours) if profile else None,
            "stress_level": _to_int(profile.stress_level) if profile else None,
            "smoking": _to_bool(profile.smoking) if profile else None,
            "alcohol": _to_bool(profile.alcohol) if profile else None,
            "appetite": profile.appetite if profile else None,
            "bowel_habits": profile.bowel_habits if profile else None,
        },
        "initial_clinical_snapshot": initial_snapshot,
        "device_connections": device_connections,
    }


def _serialize_profile(user: User, profile: Optional[UserProfile]) -> dict:
    dob_value = profile.date_of_birth.isoformat() if profile and profile.date_of_birth else None
    derived_age = _age_from_date_of_birth(profile.date_of_birth) if profile else None
    activity_level = _to_int(profile.activity_level) if profile else None
    goals = profile.goals if profile and profile.goals else None
    sections = _serialize_structured_sections(user, profile)
    user_profile_payload = sections["user_profile"]
    medical_history_payload = sections["medical_history"]
    lifestyle_payload = sections["lifestyle_profile"]
    initial_snapshot = sections["initial_clinical_snapshot"]
    device_connections = sections["device_connections"]
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
        "sex": profile.gender if profile else None,
        "occupation": profile.occupation if profile else None,
        "city": profile.city if profile else None,
        "marital_status": profile.marital_status if profile else None,
        "height_cm": _to_float(profile.height_cm) if profile else None,
        "height": _to_float(profile.height_cm) if profile else None,
        "weight_kg": _to_float(profile.weight_kg) if profile else None,
        "weight": _to_float(profile.weight_kg) if profile else None,
        "activity_level": activity_level,
        "activity": _activity_label(activity_level),
        "goals": goals,
        "diet": lifestyle_payload["diet"],
        "sleep": lifestyle_payload["sleep_hours"],
        "sleep_hours": lifestyle_payload["sleep_hours"],
        "stress": lifestyle_payload["stress_level"],
        "stress_level": lifestyle_payload["stress_level"],
        "smoking": _yes_no_label(lifestyle_payload["smoking"]),
        "alcohol": _yes_no_label(lifestyle_payload["alcohol"]),
        "appetite": lifestyle_payload["appetite"],
        "bowel_habits": lifestyle_payload["bowel_habits"],
        "conditions": medical_history_payload["conditions"],
        "family_history": profile.family_history if profile else None,
        "surgeries": medical_history_payload["surgeries"],
        "hospitalizations": medical_history_payload["hospitalizations"],
        "hospitalization_details": medical_history_payload["hospitalization_details"],
        "current_medications": medical_history_payload["medications"],
        "blood_group": profile.blood_group if profile else None,
        "allergies": profile.allergies if profile else None,
        "chief_complaint": initial_snapshot["chief_complaint"],
        "symptoms": initial_snapshot["symptoms"],
        "duration": initial_snapshot["duration"],
        "onset": initial_snapshot["onset"],
        "severity": initial_snapshot["severity"],
        "user_profile": user_profile_payload,
        "medical_history": medical_history_payload,
        "lifestyle_profile": lifestyle_payload,
        "initial_clinical_snapshot": initial_snapshot,
        "device_connections": device_connections,
        "is_email_verified": user.is_email_verified,
        "is_onboarding_done": user.is_onboarding_done,
        "onboarding_step": user.onboarding_step,
        "onboardingCompleted": user.is_onboarding_done,
        "onboardingStep": user.onboarding_step,
        "gmail_connected": bool(getattr(user, "gmail_connected", False)),
        "apple_connected": bool(getattr(user, "apple_connected", False)),
        "has_password": user.password_hash not in {"OAUTH_NO_PASSWORD", "SUPABASE_AUTH"},
        "role": getattr(user, "role", ROLE_PATIENT) or ROLE_PATIENT,
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

        if "occupation" in updates:
            profile.occupation = _clean_text(updates.get("occupation"), max_chars=150)

        if "city" in updates:
            profile.city = _clean_text(updates.get("city"), max_chars=120)

        if "marital_status" in updates:
            profile.marital_status = _clean_text(updates.get("marital_status"), max_chars=50)

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

        if "family_history" in updates:
            profile.family_history = _join_text_list(updates.get("family_history"))

        if "surgeries" in updates:
            profile.surgeries = _clean_text(updates.get("surgeries"))

        if "hospitalizations" in updates:
            profile.hospitalizations = _to_bool(updates.get("hospitalizations"))

        if "hospitalization_details" in updates:
            profile.hospitalization_details = _clean_text(updates.get("hospitalization_details"))

        if "current_medications" in updates or "medications" in updates:
            profile.current_medications = _clean_text(updates.get("current_medications", updates.get("medications")))

        if "sleep_hours" in updates or "sleep" in updates:
            sleep_hours = _to_float(updates.get("sleep_hours", updates.get("sleep")))
            if sleep_hours is not None and not 0 <= sleep_hours <= 24:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sleep hours must be between 0 and 24",
                )
            profile.sleep_hours = sleep_hours

        if "stress_level" in updates or "stress" in updates:
            stress_level = _to_int(updates.get("stress_level", updates.get("stress")))
            if stress_level is not None and not 1 <= stress_level <= 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Stress level must be between 1 and 10",
                )
            profile.stress_level = stress_level

        if "smoking" in updates:
            profile.smoking = _to_bool(updates.get("smoking"))

        if "alcohol" in updates:
            profile.alcohol = _to_bool(updates.get("alcohol"))

        if "appetite" in updates:
            profile.appetite = _clean_text(updates.get("appetite"), max_chars=20)

        if "bowel_habits" in updates:
            profile.bowel_habits = _clean_text(updates.get("bowel_habits"), max_chars=20)

        if "blood_group" in updates:
            blood_group_input = safe_input(updates.get("blood_group"), max_chars=10)
            blood_group = blood_group_input.upper() if blood_group_input else None
            profile.blood_group = blood_group or None

        if "allergies" in updates:
            profile.allergies = _join_text_list(updates.get("allergies")) or _clean_text(updates.get("allergies"))

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
