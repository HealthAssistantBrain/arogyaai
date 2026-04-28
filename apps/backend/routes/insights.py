from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from services.insights_service import InsightsService


router = APIRouter(prefix="/api/v1", tags=["Insights"])


@router.get("/insights", response_model=None)
def get_insights(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return InsightsService.get_insights(db, current_user)


@router.get("/health/insights", response_model=None)
def get_health_insights(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return InsightsService.get_health_insights(db, current_user)
