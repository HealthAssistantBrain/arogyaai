from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from routes.users import get_current_user_from_header
from services.timeline_service import build_timeline_response

router = APIRouter(prefix="/api/v1/health", tags=["Health Timeline"])


@router.get("/timeline")
def get_timeline(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return build_timeline_response(db, current_user.id)
