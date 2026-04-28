from __future__ import annotations

import logging
from typing import Any

from database.session import SessionLocal
from models import LabValue, RiskScore, User
from pipelines.baseline_pipeline.service import BaselinePipelineService
from pipelines.feature_pipeline.service import FeaturePipelineService, FeatureSnapshot
from pipelines.ml_pipeline.model_loader import ModelLoader
from pipelines.ml_pipeline.service import MLPipelineService
from pipelines.shap_pipeline.service import ShapPipelineService
from pipelines.storage_pipeline.service import StoragePipelineService
from services.health_engine import HealthEngine

logger = logging.getLogger(__name__)
engine = HealthEngine()


def _load_user(db, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if user is None:
        raise LookupError(f"User {user_id} not found")
    return user


def _serialize_baseline_record(record: Any) -> dict[str, Any]:
    return {
        "metric_name": record.metric_name,
        "mean_7d": float(record.mean_7d) if record.mean_7d is not None else None,
        "mean_30d": float(record.mean_30d) if record.mean_30d is not None else None,
        "std_dev": float(record.std_dev) if record.std_dev is not None else None,
        "sample_count": int(record.sample_count or 0),
        "calculated_at": record.calculated_at.isoformat() if record.calculated_at else None,
    }


def _serialize_shap_record(record: Any) -> dict[str, Any]:
    return {
        "feature_name": record.feature_name,
        "shap_value": float(record.shap_value),
        "abs_shap_value": float(record.abs_shap_value),
        "direction": record.direction,
        "explanation": record.explanation,
        "source_type": record.source_type,
        "calculated_at": record.calculated_at.isoformat() if record.calculated_at else None,
    }


def run_feature_pipeline(
    db,
    user: User,
    *,
    payload: dict[str, Any] | None = None,
    report_id: str | None = None,
) -> FeatureSnapshot:
    overrides = MLPipelineService._prepare_feature_overrides(payload)
    return FeaturePipelineService.build_feature_snapshot(
        db,
        user,
        overrides=overrides,
        persist=True,
        report_id=report_id,
    )


def run_ml_pipeline(
    db,
    user: User,
    features: FeatureSnapshot,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return MLPipelineService.predict_from_snapshot(
        db,
        user,
        features,
        payload=payload,
    )


def load_model_safe():
    try:
        return ModelLoader().load()
    except Exception as exc:
        logger.warning("[Orchestrator] Model loading failed: %s", exc)
        return None


def run_insights_pipeline(
    db,
    user: User,
    features: FeatureSnapshot,
    predictions: dict[str, Any],
) -> dict[str, Any]:
    baseline_payload: dict[str, Any] = {"metrics": []}
    try:
        baseline_response = BaselinePipelineService.compute_baselines(db, user, features)
        baseline_payload = baseline_response.get("data", {}) or {"metrics": []}
    except Exception as exc:
        logger.warning("[Orchestrator] Baseline computation failed for user=%s: %s", user.id, exc)

    shap_payload: dict[str, Any] = {"prediction_id": None, "values": []}
    prediction_data = predictions.get("data") or {}
    prediction_id = prediction_data.get("prediction_id")
    if prediction_id:
        risk_score = db.query(RiskScore).filter(RiskScore.id == prediction_id, RiskScore.user_id == user.id).first()
        if risk_score is not None:
            try:
                shap_response = ShapPipelineService.compute_shap(
                    db,
                    user,
                    risk_score,
                    risk_score.risk_payload or prediction_data,
                    feature_snapshot=features,
                    model_available=(risk_score.prediction_source == "ml"),
                )
                shap_payload = shap_response.get("data") or shap_payload
            except Exception as exc:
                logger.warning("[Orchestrator] SHAP generation failed for user=%s prediction=%s: %s", user.id, prediction_id, exc)

    return {
        "baseline": baseline_payload,
        "shap": shap_payload,
    }


def _fallback_risk_payload(predictions: dict[str, Any], model_risk: dict[str, Any]) -> dict[str, Any]:
    prediction_data = predictions.get("data") if isinstance(predictions, dict) else {}
    prediction_data = prediction_data if isinstance(prediction_data, dict) else {}
    existing_risks = prediction_data.get("risks") if isinstance(prediction_data.get("risks"), dict) else {}

    merged_risk = {
        **existing_risks,
        **(model_risk or {}),
    }

    if prediction_data.get("risk_score") is not None:
        try:
            merged_risk.setdefault("overall_risk_score", float(prediction_data.get("risk_score")))
        except (TypeError, ValueError):
            pass
    if prediction_data.get("risk_level") is not None:
        merged_risk.setdefault("risk_level", prediction_data.get("risk_level"))

    return merged_risk


def _select_driver_payload(
    predictions: dict[str, Any],
    insights: dict[str, Any],
    model_drivers: list[Any],
) -> list[Any]:
    shap_values = ((insights.get("shap") or {}).get("values") if isinstance(insights, dict) else None)
    if isinstance(shap_values, list) and shap_values:
        return shap_values

    prediction_data = predictions.get("data") if isinstance(predictions, dict) else {}
    prediction_drivers = prediction_data.get("drivers") if isinstance(prediction_data, dict) else None
    if isinstance(prediction_drivers, list) and prediction_drivers:
        return prediction_drivers

    return model_drivers if isinstance(model_drivers, list) else []


def _select_recommendations(
    predictions: dict[str, Any],
    drivers: list[Any],
) -> list[Any]:
    prediction_data = predictions.get("data") if isinstance(predictions, dict) else {}
    prediction_recommendations = prediction_data.get("recommendations") if isinstance(prediction_data, dict) else None
    if isinstance(prediction_recommendations, list) and prediction_recommendations:
        return prediction_recommendations
    generated = engine.generate_recommendations(drivers)
    return generated if isinstance(generated, list) else []


def _build_health_insights(
    db,
    user: User,
    *,
    features: FeatureSnapshot | None,
    predictions: dict[str, Any],
    insights: dict[str, Any],
    loaded_model: Any,
) -> dict[str, Any]:
    feature_payload = features.to_dict() if hasattr(features, "to_dict") else {}
    model_risk = engine.compute_risk(loaded_model, feature_payload)
    model_drivers = engine.compute_drivers(loaded_model, feature_payload)
    baseline_metrics = ((insights.get("baseline") or {}).get("metrics") if isinstance(insights, dict) else None)

    has_lab = (
        db.query(LabValue.id)
        .filter(LabValue.user_id == user.id)
        .order_by(LabValue.extracted_at.desc())
        .first()
        is not None
    )

    return {
        "risk": _fallback_risk_payload(predictions, model_risk) or {},
        "drivers": _select_driver_payload(predictions, insights, model_drivers) or [],
        "recommendations": _select_recommendations(
            predictions,
            _select_driver_payload(predictions, insights, model_drivers),
        )
        or [],
        "availability": engine.availability_flags(
            feature_payload=feature_payload,
            has_lab=has_lab,
            has_baseline=bool(baseline_metrics),
        ),
    }


def store_results(
    db,
    user: User,
    *,
    features: FeatureSnapshot,
    predictions: dict[str, Any],
    insights: dict[str, Any],
    health_insights: dict[str, Any] | None = None,
) -> dict[str, Any]:
    latest_feature = StoragePipelineService.latest_feature_snapshot(db, user)
    latest_risk = StoragePipelineService.latest_risk_score(db, user)
    latest_health = StoragePipelineService.latest_health_score(db, user)
    latest_baselines = StoragePipelineService.latest_baseline_metrics(db, user)

    prediction_data = predictions.get("data") or {}
    prediction_id = prediction_data.get("prediction_id")
    shap_values = StoragePipelineService.latest_shap_values(db, prediction_id) if prediction_id else []

    return {
        "feature_snapshot": latest_feature.feature_payload if latest_feature is not None else features.to_dict(),
        "prediction": prediction_data,
        "health_score": float(latest_health.score) if latest_health is not None else prediction_data.get("health_score"),
        "risk_score": float(latest_risk.overall_score) if latest_risk is not None else prediction_data.get("risk_score"),
        "baseline_metrics": [_serialize_baseline_record(item) for item in latest_baselines],
        "shap_values": [_serialize_shap_record(item) for item in shap_values],
        "insights": insights,
        "health_insights": health_insights or {"risk": {}, "drivers": [], "recommendations": [], "availability": {"has_wearable": False, "has_lab": False, "has_baseline": False}},
        "last_updated": latest_health.calculated_at.isoformat() if latest_health and latest_health.calculated_at else None,
    }


def run_pipeline(
    user_id: str,
    payload: dict[str, Any] | None = None,
    report_id: str | None = None,
) -> dict[str, Any]:
    db = SessionLocal()
    try:
        user = _load_user(db, str(user_id))
        features: FeatureSnapshot | None = None
        predictions: dict[str, Any] = {
            "success": True,
            "status": "fallback",
            "source": "pipeline",
            "error": None,
            "data": {
                "risk_score": None,
                "risk_level": "UNKNOWN",
                "risks": {},
                "drivers": [],
                "recommendations": [],
            },
        }
        insights: dict[str, Any] = {
            "baseline": {"metrics": []},
            "shap": {"prediction_id": None, "values": []},
        }

        try:
            features = run_feature_pipeline(db, user, payload=payload, report_id=report_id)
        except Exception as exc:
            logger.exception("[Orchestrator] Feature pipeline failed for user=%s: %s", user.id, exc)

        loaded_model = load_model_safe()

        if features is not None:
            try:
                predictions = run_ml_pipeline(db, user, features, payload=payload) or predictions
            except Exception as exc:
                logger.exception("[Orchestrator] ML pipeline failed for user=%s: %s", user.id, exc)

            try:
                insights = run_insights_pipeline(db, user, features, predictions) or insights
            except Exception as exc:
                logger.exception("[Orchestrator] Insights pipeline failed for user=%s: %s", user.id, exc)

        health_insights = _build_health_insights(
            db,
            user,
            features=features,
            predictions=predictions,
            insights=insights,
            loaded_model=loaded_model,
        )

        prediction_data = predictions.get("data") if isinstance(predictions, dict) else {}
        prediction_id = prediction_data.get("prediction_id") if isinstance(prediction_data, dict) else None
        try:
            StoragePipelineService.store_health_insights(
                db,
                user,
                health_insights,
                prediction_id=prediction_id,
            )
        except Exception as exc:
            logger.warning("[Orchestrator] Health insights persistence failed for user=%s: %s", user.id, exc)

        safe_features = features or FeatureSnapshot.from_dict({})
        stored_results = store_results(
            db,
            user,
            features=safe_features,
            predictions=predictions,
            insights=insights,
            health_insights=health_insights,
        )
        return {
            "status": "completed",
            "user_id": str(user.id),
            "result": stored_results,
        }
    finally:
        db.close()
