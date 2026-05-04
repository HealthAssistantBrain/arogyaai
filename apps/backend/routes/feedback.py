from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.session import get_db
from models import FeedbackEntityType, User
from routes.users import get_current_user_from_header
from schemas.feedback import FeedbackCreate, FeedbackListResponse, FeedbackResponse, FeedbackStatsResponse
from services.feedback_service import FeedbackEntityNotFoundError, FeedbackService


router = APIRouter(prefix="/api/v1/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    try:
        return FeedbackService.create_feedback(db, current_user, payload)
    except FeedbackEntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("", response_model=FeedbackListResponse)
@router.get("/", response_model=FeedbackListResponse)
async def list_feedback(
    entity_type: FeedbackEntityType | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    rows = FeedbackService.get_feedback_by_user(
        db,
        current_user,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )
    return {"feedback": rows, "count": len(rows)}


@router.get("/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(
    entity_type: FeedbackEntityType | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return FeedbackService.aggregate_feedback_stats(
        db,
        current_user,
        entity_type=entity_type,
        entity_id=entity_id,
    )


@router.get("/analytics", response_model=None)
async def get_feedback_analytics(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "status": "ready",
        "source": "feedback_service",
        "error": None,
        "data": {
            "average_rating_per_model": FeedbackService.average_rating_per_model(db, current_user),
            "incorrect_prediction_rate": FeedbackService.incorrect_prediction_rate(db, current_user),
            "explanation_helpfulness_score": FeedbackService.explanation_helpfulness_score(db, current_user),
        },
    }


@router.get("/{entity_id}", response_model=FeedbackListResponse)
async def get_feedback_for_entity(
    entity_id: UUID,
    entity_type: FeedbackEntityType | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    rows = FeedbackService.get_feedback_by_entity(
        db,
        current_user,
        entity_id,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )
    return {"feedback": rows, "count": len(rows)}
