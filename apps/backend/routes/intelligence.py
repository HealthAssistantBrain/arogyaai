from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.api_models import PredictionRequest, PredictionResponse, ExplanationRequest, ExplanationResponse
from services.prediction_explanation_service import PredictionExplanationService

router = APIRouter(prefix="/api/v1/intelligence", tags=["Intelligence"])

from services import intelligence_service as svc

@router.post("/predict", response_model=None)
async def predict_risk(data: PredictionRequest):
    """Triggers ML prediction via IntelligenceService."""
    return await svc.get_risk_prediction(data)

@router.post("/explain", response_model=None)
async def explain_prediction(
    req: ExplanationRequest,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    """Triggers AI explanation via IntelligenceService."""
    return await PredictionExplanationService.get_prediction_explanation(
        db,
        current_user,
        prediction_id=str(req.prediction_id),
    )
