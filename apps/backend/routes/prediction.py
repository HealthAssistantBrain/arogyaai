from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.api_models import PredictionRequest, PredictionResponse

router = APIRouter(prefix="/prediction", tags=["Prediction"])

@router.post("/compute", response_model=PredictionResponse)
async def compute_prediction(
    req: PredictionRequest, 
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db)
):
    """
    Computes health risk prediction based on user data points.
    Invoked during onboarding summary completion.
    """
    # In a real system, this would trigger a ML microservice.
    # For now, we return a mock response to unblock the frontend flow.
    
    # Optionally update the user's onboarding status here if needed, 
    # but the frontend usually handles the transition.
    
    return {
        "risk_score": 45.2,
        "risk_level": "Moderate",
        "recommendations": [
            "Maintain current activity level",
            "Schedule a routine check-up in 6 months",
            "Focus on consistent sleep patterns"
        ]
    }
