from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.api_models import DiseaseSimulationRequest, PredictionRequest, PredictionResponse

router = APIRouter(prefix="/api/v1/prediction", tags=["Prediction"])

from services.disease_simulation_service import DiseaseSimulationService
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


@router.get("/simulator/baseline", response_model=None)
def get_simulator_baseline(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    baseline = DiseaseSimulationService.build_baseline(db, current_user)
    return {
        "success": True,
        "status": "ready",
        "source": "db+rule_engine",
        "error": None,
        "data": {
            "baseline": baseline["baseline"].as_dict(),
            "profile": baseline["profile"],
            "medical_conditions": baseline["conditions"],
            "focus_options": baseline["focus_options"],
            "assumptions": baseline["assumptions"],
        },
    }


@router.post("/simulator/run", response_model=None)
def run_disease_simulation(
    req: DiseaseSimulationRequest,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return DiseaseSimulationService.simulate(db, current_user, req)
