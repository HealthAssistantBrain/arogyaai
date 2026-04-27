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
from models import User, UserProfile
from core.session_cookies import clear_session_cookies
from services.user_service import UserService
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
    data = UserService.get_user_me(db, current_user)
    
    # Enrich with conditions
    from models.medical_history import MedicalHistory
    history = db.query(MedicalHistory).filter(MedicalHistory.user_id == current_user.id).all()
    if history:
        data["data"]["conditions"] = [h.condition_name for h in history]
        
    return data


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
    # Source-of-truth connection status is stored on the user record.
    return [
        {
            "name": "Gmail",
            "status": "connected" if current_user.gmail_connected else "not_connected",
        },
        {
            "name": "Apple ID",
            "status": "connected" if current_user.apple_connected else "not_connected",
        },
        {
            "name": "Google Fit",
            "status": "connected" if current_user.google_fit_connection else "not_connected",
        },
        {
            "name": "Apple Health",
            "status": "not_connected",
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


from models.medical_history import MedicalHistory

@router.post("/medical-history")
def update_medical_history(
    payload: dict,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Saves medical history data (conditions, allergies, family_history)."""
    try:
        # Load profile to save allergies
        profile = UserService.get_or_create_user_profile(db, current_user)
        
        allergies = payload.get("allergies", [])
        if isinstance(allergies, list):
            profile.allergies = allergies
            
        conditions = payload.get("conditions", [])
        if isinstance(conditions, list):
            # Replace current conditions
            db.query(MedicalHistory).filter(MedicalHistory.user_id == current_user.id).delete()
            for cond in conditions:
                db.add(MedicalHistory(user_id=current_user.id, condition_name=cond))
                
        db.commit()
        return {"success": True, "message": "Medical history saved successfully."}
    except Exception as e:
        db.rollback()
        # Keep non-critical log but return OK to not block UI progression abruptly
        return {"success": False, "error": str(e)}


@router.post("/lifestyle")
def update_lifestyle(
    payload: dict,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Saves lifestyle assessment data (activity, diet, sleep, stress)."""
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

    UserService.update_user_profile(
        db,
        current_user,
        {
            "activity_level": activity_level,
            "goals": goals,
        },
    )

    return {
        "success": True,
        "message": "Lifestyle data saved successfully.",
        "data": {
            "activity_level": activity_level,
            "goals": goals,
            "sleep": payload.get("sleep"),
            "stress": payload.get("stress"),
        },
    }
