from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.clinical_history import ClinicalHistoryCreate
from services.clinical_history_service import ClinicalHistoryService

router = APIRouter(prefix="/api/v1/clinical-history", tags=["Clinical History"])


@router.post("")
def create_clinical_history(
    payload: ClinicalHistoryCreate,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    data = ClinicalHistoryService.create_history(db, current_user, payload)
    return {
        "success": True,
        "status": "ready",
        "source": "db+clinical_rules",
        "error": None,
        "data": data,
    }


@router.get("")
def list_clinical_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    data = ClinicalHistoryService.list_histories(db, current_user, limit=limit)
    return {
        "success": True,
        "status": "ready" if data else "empty",
        "source": "db",
        "error": None,
        "data": data,
    }
