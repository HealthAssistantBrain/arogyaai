from fastapi import APIRouter
from schemas.api_models import PredictionRequest, PredictionResponse, ExplanationRequest, ExplanationResponse

router = APIRouter(prefix="/api/v1/intelligence", tags=["Intelligence"])

from services import intelligence_service as svc

@router.post("/predict", response_model=None)
async def predict_risk(data: PredictionRequest):
    """Triggers ML prediction via IntelligenceService."""
    return await svc.get_risk_prediction(data)

@router.post("/explain", response_model=None)
async def explain_prediction(req: ExplanationRequest):
    """Triggers AI explanation via IntelligenceService."""
    return await svc.get_explanation(req)
