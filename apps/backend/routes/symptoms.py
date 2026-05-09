from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.symptom_analysis import SaveSymptomAnalysisToTimelineRequest, SymptomAnalysisCreate
from services.symptom_analysis import SymptomAnalysisService

router = APIRouter(prefix="/api/v1/symptoms", tags=["Symptom Analysis"])


@router.post("/analyze")
async def analyze_symptoms(
    payload: SymptomAnalysisCreate,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    data = await SymptomAnalysisService.analyze(db, current_user, payload)
    return {
        "success": True,
        "status": "ready",
        "source": "db+symptom_analysis_pipeline",
        "error": None,
        "data": data,
    }


@router.get("/history")
def get_symptom_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    data = SymptomAnalysisService.get_history(db, current_user, limit=limit)
    return {
        "success": True,
        "status": "ready" if data else "empty",
        "source": "db",
        "error": None,
        "data": data,
    }


@router.get("/{session_id}")
def get_symptom_session(
    session_id: str,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    data = SymptomAnalysisService.get_one(db, current_user, session_id)
    return {
        "success": True,
        "status": "ready",
        "source": "db",
        "error": None,
        "data": data,
    }


@router.post("/{session_id}/timeline")
def save_symptom_session_to_timeline(
    session_id: str,
    payload: SaveSymptomAnalysisToTimelineRequest,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    data = SymptomAnalysisService.save_to_timeline(db, current_user, session_id, force=payload.force)
    return {
        "success": True,
        "status": "ready",
        "source": "db+timeline",
        "error": None,
        "data": data,
    }
