from fastapi import APIRouter
from schemas.api_models import PredictionRequest, PredictionResponse, ExplanationRequest, ExplanationResponse

router = APIRouter(tags=["Intelligence"])

@router.post("/predict", response_model=PredictionResponse)
async def predict_risk(data: PredictionRequest):
    # TODO: Proxy to Prediction Microservice
    return {
        "risk_score": 82.5,
        "risk_level": "High",
        "recommendations": ["Consult a specialist", "Reduce sodium intake"]
    }

@router.post("/explain", response_model=ExplanationResponse)
async def explain_prediction(req: ExplanationRequest):
    # TODO: Proxy to RAG Microservice
    return {
        "factors": [{"name": "blood_pressure", "impact": "+15%"}],
        "summary": "The primary drivers are elevated systolic pressure and family history."
    }
