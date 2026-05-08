from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.auth import get_current_user_from_header
from database.session import get_db
from models import User
from services.profile_service import ProfileService

router = APIRouter(prefix="/api/v1/profile", tags=["Profile"])


@router.get("")
def get_profile_bundle(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return ProfileService.get_profile_bundle(db, current_user)
