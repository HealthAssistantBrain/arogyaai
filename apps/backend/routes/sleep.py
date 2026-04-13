from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from services.sleep_service import SleepService


router = APIRouter(prefix="/api/v1/sleep", tags=["Sleep"])


@router.get("/summary")
def get_sleep_summary(
    range: str = Query(default="24h", pattern="^(24h|7d|30d)$"),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return SleepService.get_sleep_summary(db, current_user, range_value=range)

