"""
user_data.py — canonical user profile, onboarding, settings, and vitals routes.
"""
from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.api_models import UserOnboardingSave, UserProfileUpdate, UserSettingsUpdate, ProfileUpdateSchema
from services.onboarding_service import OnboardingService
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
    return UserDataService.update_profile(
        db,
        user,
        {
            "full_name": payload.full_name,
            "phone": payload.phone,
            "date_of_birth": payload.date_of_birth,
            "height": payload.height,
            "weight": payload.weight,
            "gender": payload.gender,
            "blood_group": payload.blood_group,
            "allergies": payload.allergies,
        },
    )


@router.post("/onboarding")
def save_onboarding(
    payload: UserOnboardingSave,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return UserDataService.save_onboarding(db, current_user, payload.model_dump(exclude_unset=True))

@router.post("/complete-onboarding")
def complete_onboarding(
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return OnboardingService.finalize_onboarding(db, current_user, payload)


@router.post("/onboarding-complete")
def complete_onboarding_legacy(
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return OnboardingService.finalize_onboarding(db, current_user, payload)


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
