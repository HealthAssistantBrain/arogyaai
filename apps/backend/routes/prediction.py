from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.session import get_db
from models import RiskScore, User
from pipelines.ml_pipeline.service import MLPipelineService
from pipelines.storage_pipeline.service import StoragePipelineService
from routes.users import get_current_user_from_header
from schemas.api_models import DiseaseSimulationRequest, PredictionRequest, PredictionResponse
from services.audit_service import log_event
from services.progressive_ai_service import ProgressiveAIService
from services.prediction_explanation_service import PredictionExplanationService

router = APIRouter(prefix="/api/v1/prediction", tags=["Prediction"])

from services.disease_simulation_service import DiseaseSimulationService
from services.prediction_service import get_health_prediction
from pipelines.orchestration_pipeline.service import OrchestrationPipelineService
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
    return await get_health_prediction(str(current_user.id), req, db=db, current_user=current_user)


@router.post("/run", response_model=None)
async def run_prediction(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    try:
        snapshot = StoragePipelineService.latest_feature_snapshot(db, current_user)
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No feature snapshot available for this user.",
            )

        result = MLPipelineService.predict_from_snapshot_record(db, current_user, snapshot)
        result = await PredictionExplanationService.hydrate_prediction_response(db, current_user, result)
        data = result.get("data") or {}
        response_payload = {
            "risk_score": data.get("risk_score"),
            "factors": data.get("factors") or [],
        }
        log_event(
            current_user.id,
            "prediction_run",
            "/api/v1/prediction/run",
            {
                "status": "success",
                "prediction_id": data.get("prediction_id"),
                "risk_score": data.get("risk_score"),
                "factor_count": len(response_payload["factors"]),
                "feature_snapshot_id": getattr(snapshot, "id", None),
            },
        )
        return response_payload
    except Exception as exc:
        log_event(
            current_user.id,
            "prediction_run",
            "/api/v1/prediction/run",
            {
                "status": "failed",
                "error": str(exc),
            },
        )
        raise


@router.post("/trigger", response_model=None)
async def trigger_prediction_pipeline(
    req: PredictionRequest,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    context = {
        "user_id": str(current_user.id),
        "payload": req.model_dump(),
    }
    result = OrchestrationPipelineService.trigger_prediction(context)
    log_event(
        current_user.id,
        "prediction_run",
        "/api/v1/prediction/trigger",
        {
            "status": result.get("status"),
            "task_id": result.get("data", {}).get("task_id"),
            "source": result.get("source"),
            "queued_payload_keys": sorted((req.model_dump() or {}).keys()),
        },
    )
    return result


@router.get("/status/{task_id}", response_model=None)
def get_prediction_status(
    task_id: str,
    current_user: User = Depends(get_current_user_from_header),
):
    return OrchestrationPipelineService.get_status(task_id)


@router.get("/shap/{prediction_id}", response_model=None)
def get_prediction_shap(
    prediction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header),
):
    risk_score = db.query(RiskScore).filter(RiskScore.id == prediction_id, RiskScore.user_id == current_user.id).first()
    if risk_score is None:
        return {
            "success": True,
            "status": "fallback",
            "source": "rule_fallback",
            "error": None,
            "data": {
                "prediction_id": prediction_id,
                "values": [],
            },
        }

    shap_rows = StoragePipelineService.latest_shap_values(db, prediction_id)
    if not shap_rows:
        return {
            "success": True,
            "status": "fallback",
            "source": "rule_fallback",
            "error": None,
            "data": {
                "prediction_id": prediction_id,
                "values": [],
            },
        }

    return {
        "success": True,
        "status": "ready",
        "source": shap_rows[0].source_type if shap_rows else "rule_fallback",
        "error": None,
        "data": {
            "prediction_id": prediction_id,
            "values": [
                {
                    "feature_name": row.feature_name,
                    "shap_value": float(row.shap_value),
                    "abs_shap_value": float(row.abs_shap_value),
                    "direction": row.direction,
                    "explanation": row.explanation,
                    "source_type": row.source_type,
                    "calculated_at": row.calculated_at.isoformat() if row.calculated_at else None,
                }
                for row in shap_rows
            ],
        },
    }


@router.get("/explanation", response_model=None)
async def get_prediction_explanation(
    prediction_id: str | None = Query(default=None),
    force_refresh: bool = Query(default=False),
    background: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header),
):
    if background:
        return await ProgressiveAIService.get_prediction_explanation(
            db,
            current_user,
            prediction_id=prediction_id,
            force_refresh=force_refresh,
        )
    return await PredictionExplanationService.get_prediction_explanation(
        db,
        current_user,
        prediction_id=prediction_id,
        force_refresh=force_refresh,
    )


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
