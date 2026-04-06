"""
user_data.py — canonical user profile, onboarding, settings, and vitals routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.api_models import UserOnboardingSave, UserProfileUpdate, UserSettingsUpdate
from services.user_data_service import UserDataService

router = APIRouter(prefix="/api/v1/user", tags=["User Data"])


@router.get("/profile")
def get_profile(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return UserDataService.get_profile(db, current_user)


@router.put("/profile")
def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return UserDataService.update_profile(db, current_user, payload.model_dump(exclude_unset=True))


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
