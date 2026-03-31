from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.api_models import PredictionRequest, PredictionResponse

router = APIRouter(prefix="/api/v1/prediction", tags=["Prediction"])

from services.prediction_service import get_health_prediction

@router.post("/compute", response_model=None)
async def compute_prediction(
    req: PredictionRequest, 
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db)
):
    """
    Computes health risk prediction via PredictionService.
    Invoked during onboarding summary completion.
    """
    return await get_health_prediction(str(current_user.id), req)
