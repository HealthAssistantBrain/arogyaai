"""
user_data.py — canonical user profile, onboarding, settings, and vitals routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.api_models import UserOnboardingSave, UserProfileUpdate, UserSettingsUpdate, ProfileUpdateSchema
from services.user_data_service import UserDataService
from services.user_service import UserService

router = APIRouter(prefix="/api/v1/user", tags=["User Data"])


@router.get("/profile")
def get_profile(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return UserDataService.get_profile(db, current_user)


@router.put("/profile")
def update_profile(
    payload: ProfileUpdateSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_header)
):
    profile = UserService.get_or_create_user_profile(db, user)
    
    if payload.full_name is not None:
        user.full_name = payload.full_name
        profile.full_name = payload.full_name
    
    if payload.phone is not None:
        profile.phone = payload.phone
        
    if payload.date_of_birth is not None:
        try:
            from datetime import datetime
            profile.date_of_birth = datetime.strptime(payload.date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            pass
            
    if payload.height is not None:
        profile.height = payload.height
        
    if payload.weight is not None:
        profile.weight = payload.weight
        
    if payload.gender is not None:
        profile.gender = payload.gender
        
    if payload.blood_group is not None:
        profile.blood_group = payload.blood_group
        
    if payload.allergies is not None:
        profile.allergies = payload.allergies

    # COMMIT TO DATABASE (User's required step)
    db.add(user)
    db.add(profile)
    db.commit()
    db.refresh(user)
    db.refresh(profile)

    dob_value = profile.date_of_birth.isoformat() if profile.date_of_birth else None

    response_data = {
        "full_name": user.full_name,
        "phone": profile.phone,
        "date_of_birth": dob_value,
        "dob": dob_value,
        "height": float(profile.height) if profile.height else None,
        "weight": float(profile.weight) if profile.weight else None,
        "gender": profile.gender,
        "blood_group": profile.blood_group,
        "allergies": profile.allergies
    }
    
    return {
        "success": True,
        "data": response_data
    }


@router.post("/onboarding")
def save_onboarding(
    payload: UserOnboardingSave,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return UserDataService.save_onboarding(db, current_user, payload.model_dump(exclude_unset=True))


@router.get("/settings")
def get_settings(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return UserDataService.get_settings(db, current_user)


@router.put("/settings")
def update_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return UserDataService.update_settings(db, current_user, payload.model_dump())
