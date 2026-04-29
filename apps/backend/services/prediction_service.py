from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from core.pipeline_logger import log_pipeline
from models import User
from pipelines.ml_pipeline.service import MLPipelineService
from schemas.api_models import PredictionRequest
from services.audit_service import log_event
from services.prediction_explanation_service import PredictionExplanationService

logger = logging.getLogger("uvicorn.error")


async def get_health_prediction(
    user_id: str,
    data: PredictionRequest,
    db: Session | None = None,
    current_user: User | None = None,
) -> Dict[str, Any]:
    """
    Coordinates health risk prediction through the local hybrid pipeline.

    Requires a DB session and resolved user because the ML pipeline persists
    feature, risk, SHAP, and health-score outputs as part of the request flow.
    """
    payload = data.model_dump()
    payload["user_id"] = user_id

    if db is None or current_user is None:
        raise RuntimeError("Prediction requests require a database session and authenticated user.")

    log_pipeline("ml", step="predict", status="running", data="pending")
    try:
        result = MLPipelineService.predict(db, current_user, payload)
        result = await PredictionExplanationService.hydrate_prediction_response(db, current_user, result)
        log_pipeline("ml", step="predict", status="healthy", data="fetched")
        result_data = result.get("data") or {}
        log_event(
            current_user.id,
            "prediction_run",
            "/api/v1/prediction/compute",
            {
                "status": "success",
                "prediction_id": result_data.get("prediction_id"),
                "risk_score": result_data.get("risk_score"),
                "health_score": result_data.get("health_score"),
                "input_keys": sorted(payload.keys()),
            },
        )
        return result
    except Exception as exc:
        log_pipeline("ml", step="predict", status="unhealthy", data="failed")
        log_event(
            current_user.id,
            "prediction_run",
            "/api/v1/prediction/compute",
            {
                "status": "failed",
                "error": str(exc),
                "input_keys": sorted(payload.keys()),
            },
        )
        logger.exception("MLPipeline prediction failed for user=%s: %s", user_id, exc)
        raise
