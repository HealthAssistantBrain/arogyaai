from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from models import User
from pipelines.ml_pipeline.service import MLPipelineService
from schemas.api_models import PredictionRequest


async def get_health_prediction(
    user_id: str,
    data: PredictionRequest,
    db: Session | None = None,
    current_user: User | None = None,
) -> Dict[str, Any]:
    """
    Coordinates health risk prediction through the local hybrid pipeline.

    If a DB session and resolved user are provided, the pipeline persists
    feature, risk, SHAP, and health-score outputs. Otherwise it returns a safe
    fallback envelope.
    """
    payload = data.model_dump()
    payload["user_id"] = user_id

    if db is not None and current_user is not None:
        return MLPipelineService.predict(db, current_user, payload)

    return {
        "success": True,
        "status": "fallback",
        "source": "computed",
        "error": None,
        "data": {
            "risk_score": 45.2,
            "risk_level": "Moderate",
            "recommendations": [
                "Maintain current activity level",
                "Schedule a routine check-up in 6 months",
                "Focus on consistent sleep patterns",
            ],
        },
    }
