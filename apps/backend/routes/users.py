"""
users.py — User routes

Exposes:
  GET /users/me       ← called by frontend hydrateAuth() on every boot
  PUT /users/me       ← profile update (stub)
  DELETE /users/me    ← account deletion (stub)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Header as FastAPIHeader
from sqlalchemy.orm import Session

from database.session import get_db
from models import MedicalHistory, User, UserProfile
from core.session_cookies import clear_session_cookies
from services.user_service import UserService
from services.clinical_history_service import ClinicalHistoryService
from services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

def get_supabase_claims_from_header(
    request: Request,
    authorization: str = FastAPIHeader(None),
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    else:
        token = None

    if not token:
        raise credentials_exception

    try:
        return AuthService._decode_supabase_token(token)
    except HTTPException:
        raise credentials_exception

def get_current_user_from_header(
    claims: dict = Depends(get_supabase_claims_from_header),
    db: Session = Depends(get_db),
) -> User:
    return AuthService.get_or_create_user_from_supabase_claims(db, claims)


def get_existing_user_from_header(
    claims: dict = Depends(get_supabase_claims_from_header),
    db: Session = Depends(get_db),
) -> User:
    user = AuthService.get_user_from_supabase_claims(db, claims)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user has not been synchronized yet",
        )
    return user


def get_current_user_profile(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
) -> UserProfile:
    return UserService.get_or_create_user_profile(db, current_user)


def get_current_user(
    current_profile: UserProfile = Depends(get_current_user_profile),
) -> UserProfile:
    return current_profile


@router.get("/me")
def get_me(
    current_user: User = Depends(get_existing_user_from_header),
    db: Session = Depends(get_db),
):
    """Returns the authenticated user's core profile data via UserService."""
    return UserService.get_user_me(db, current_user)


@router.post("/create-from-auth")
def create_from_auth(
    claims: dict = Depends(get_supabase_claims_from_header),
    db: Session = Depends(get_db),
):
    """Create or link the authenticated Supabase user in an idempotent way."""
    current_user = AuthService.get_or_create_user_from_supabase_claims(db, claims)
    return UserService.get_user_me(db, current_user)


@router.get("/devices")
def get_user_devices(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Return user's connected devices status."""
    from services.google_fit_service import GoogleFitService

    google_fit_status = GoogleFitService.get_status(db, current_user)
    google_fit_connected = bool(google_fit_status.get("connected"))

    return [
        {
            "name": "Gmail",
            "provider": "gmail",
            "status": "connected" if current_user.gmail_connected else "not_connected",
            "is_connected": bool(current_user.gmail_connected),
        },
        {
            "name": "Apple ID",
            "provider": "apple-id",
            "status": "connected" if current_user.apple_connected else "not_connected",
            "is_connected": bool(current_user.apple_connected),
        },
        {
            "name": "Google Fit",
            "provider": "google-fit",
            "status": "connected" if google_fit_connected else "not_connected",
            "is_connected": google_fit_connected,
            "last_synced_at": google_fit_status.get("last_synced_at"),
        },
        {
            "name": "Apple Health",
            "provider": "apple-health",
            "status": "not_connected",
            "is_connected": False,
        },
    ]


@router.put("/me")
def update_me(
    updates: dict,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Update mutable profile fields via UserService."""
    return UserService.update_user_me(db, current_user, updates)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    response: Response,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Deactivate user via UserService."""
    UserService.delete_user_me(db, current_user)
    clear_session_cookies(response)
    return None


@router.post("/profile")
def update_profile(
    updates: dict,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Upserts extending user profile via UserService."""
    return UserService.update_user_profile(db, current_user, updates)

@router.post("/medical-history")
def update_medical_history(
    payload: dict,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Saves structured medical history while keeping the existing conditions storage intact."""
    try:
        profile_updates = {
            "allergies": payload.get("allergies"),
            "family_history": payload.get("family_history"),
            "surgeries": payload.get("surgeries"),
            "hospitalizations": payload.get("hospitalizations"),
            "hospitalization_details": payload.get("hospitalization_details"),
            "current_medications": payload.get("current_medications", payload.get("medications")),
        }
        UserService.update_user_profile(db, current_user, profile_updates)

        conditions = payload.get("conditions", [])
        if isinstance(conditions, list):
            db.query(MedicalHistory).filter(MedicalHistory.user_id == current_user.id).delete()
            for cond in conditions:
                normalized = str(cond or "").strip()
                if normalized:
                    db.add(MedicalHistory(user_id=current_user.id, condition_name=normalized))

        db.commit()
        return UserService.get_user_me(db, current_user)
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}


@router.post("/lifestyle")
def update_lifestyle(
    payload: dict,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Saves lifestyle assessment plus the optional onboarding clinical snapshot."""
    activity_raw = payload.get("activity")
    if isinstance(activity_raw, str):
        normalized_activity = activity_raw.strip().lower()
        activity_level = {
            "sedentary": 3500,
            "active": 8000,
            "very active": 12000,
        }.get(normalized_activity)
    else:
        try:
            activity_level = int(activity_raw) if activity_raw is not None else None
        except (TypeError, ValueError):
            activity_level = None

    diet = payload.get("diet")
    goals = None
    if isinstance(diet, list):
        goals = ", ".join(str(item).strip() for item in diet if str(item).strip())
    elif isinstance(diet, str):
        goals = diet.strip() or None

    result = UserService.update_user_profile(
        db,
        current_user,
        {
            "activity_level": activity_level,
            "goals": goals,
            "sleep_hours": payload.get("sleep"),
            "stress_level": payload.get("stress"),
            "smoking": payload.get("smoking"),
            "alcohol": payload.get("alcohol"),
            "appetite": payload.get("appetite"),
            "bowel_habits": payload.get("bowel_habits"),
        },
    )

    clinical_snapshot = ClinicalHistoryService.upsert_initial_snapshot(
        db,
        current_user,
        {
            "chief_complaint": payload.get("chief_complaint"),
            "associated_symptoms": payload.get("symptoms", payload.get("associated_symptoms", [])),
            "duration_value": payload.get("duration_value"),
            "duration_unit": payload.get("duration_unit"),
            "onset": payload.get("onset"),
            "severity": payload.get("severity"),
        },
    )

    return {
        "success": True,
        "message": "Lifestyle data saved successfully.",
        "data": {
            "activity_level": activity_level,
            "goals": goals,
            "lifestyle_profile": (result.get("data") or {}).get("lifestyle_profile"),
            "initial_clinical_snapshot": clinical_snapshot,
        },
    }
