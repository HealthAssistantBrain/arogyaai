from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import sys
from typing import Any

from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "apps" / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models import FeatureSnapshotRecord
from models import User
from pipelines.feature_pipeline.service import FeaturePipelineService, FeatureSnapshot
from pipelines.ml_pipeline.inference import MLPipelineInference
from pipelines.ml_pipeline.model_loader import ModelLoader
from pipelines.ml_pipeline.preprocess import build_feature_vector
from pipelines.ml_pipeline.shap_explainer import ShapExplainer
from pipelines.storage_pipeline.service import StoragePipelineService
from services.alert_service import generate_health_alerts

logger = logging.getLogger("uvicorn.error")


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _risk_level(score: float) -> str:
    normalized = score / 100.0 if score > 1 else score
    if normalized > 0.80:
        return "HIGH"
    if normalized >= 0.50:
        return "MODERATE"
    return "LOW"


def _risk_key(model_type: str) -> str:
    if model_type == "cardio":
        return "cardiovascular"
    return model_type


def _risk_label(model_type: str) -> str:
    labels = {
        "diabetes": "Diabetes",
        "cardio": "Cardiovascular",
        "sleep": "Sleep",
    }
    return labels.get(model_type, model_type.title())


def _condition_risk_key(model_type: str) -> str:
    return f"{model_type}_risk"


def _risk_value(risks: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in risks:
            return risks[key]
    return None


class MLPipelineService:
    @staticmethod
    def _prepare_feature_overrides(payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        data_points = payload.get("data_points") if isinstance(payload.get("data_points"), dict) else {}
        if not isinstance(data_points, dict):
            data_points = {}

        overrides: dict[str, Any] = {}
        for key in (
            "avg_hrv",
            "avg_rhr",
            "sleep_score",
            "sleep_duration",
            "sleep",
            "activity_level",
            "bmi",
            "systolic_bp",
            "diastolic_bp",
            "age",
            "sex",
            "stress",
            "cholesterol_proxy",
            "cholesterol",
            "glucose",
            "hba1c",
            "heart_rate",
            "steps",
            "sleep_hours",
            "height",
            "weight",
            "hr_mean_7d",
            "steps_avg_7d",
            "sleep_efficiency",
            "lifestyle_score",
            "activity_score",
            "disease_flags",
            "family_history_flags",
            "symptom_flags",
            "severity_score",
        ):
            if key in data_points:
                overrides[key] = data_points[key]

        return overrides

    @staticmethod
    def _compute_health_score(feature_snapshot: Any, risk_payload: dict[str, Any]) -> dict[str, Any]:
        cards = risk_payload.get("cards") or []
        card_scores = [float(card.get("score") or 0.0) for card in cards if isinstance(card, dict)]
        if card_scores:
            avg_risk = sum(card_scores) / len(card_scores)
        else:
            avg_risk = float(risk_payload.get("overall_score") or risk_payload.get("risk_score") or 0.0)

        if avg_risk <= 1.0:
            avg_risk *= 100.0
        risk_component = _clamp(100.0 - avg_risk, 0.0, 100.0)

        lifestyle_component = getattr(feature_snapshot, "lifestyle_score", None)
        if lifestyle_component is None:
            lifestyle_component = getattr(feature_snapshot, "activity_score", None) or getattr(feature_snapshot, "sleep_efficiency", None) or 60.0

        vitals_component = 60.0
        avg_rhr = getattr(feature_snapshot, "avg_rhr", None)
        avg_hrv = getattr(feature_snapshot, "avg_hrv", None)
        if avg_rhr is not None:
            vitals_component += max(0.0, 65.0 - float(avg_rhr)) * 1.5
            vitals_component -= max(0.0, float(avg_rhr) - 65.0) * 2.0
        if avg_hrv is not None:
            vitals_component += max(0.0, float(avg_hrv) - 50.0) * 0.6
        vitals_component = _clamp(vitals_component, 0.0, 100.0)

        sleep_component = getattr(feature_snapshot, "sleep_efficiency", None)
        if sleep_component is None:
            sleep_component = getattr(feature_snapshot, "sleep_score", None) or 60.0

        health_score = _clamp(
            risk_component * 0.4 + float(lifestyle_component) * 0.25 + vitals_component * 0.2 + float(sleep_component) * 0.15,
            0.0,
            100.0,
        )

        return {
            "score": round(health_score, 2),
            "risk_component": round(risk_component, 2),
            "lifestyle_component": round(float(lifestyle_component), 2),
            "vitals_component": round(vitals_component, 2),
            "sleep_component": round(float(sleep_component), 2),
        }

    @staticmethod
    def _compose_response(
        *,
        user: User,
        feature_snapshot: Any,
        risk_payload: dict[str, Any],
        risk_score_record: Any,
        health_score_record: Any,
        model_version: str | None,
        source: str,
        factors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        overall_score = float(risk_payload.get("overall_score") or risk_payload.get("risk_score") or 0.0)
        risk_level = str(risk_payload.get("risk_level") or _risk_level(overall_score)).upper()
        feature_payload = MLPipelineService._feature_snapshot_payload(feature_snapshot)
        data_availability = feature_payload.get("data_availability") if isinstance(feature_payload, dict) else {}

        data = {
            "user_id": str(user.id),
            "prediction_id": str(risk_score_record.id),
            "health_score_id": str(health_score_record.id),
            "risk_score": round(overall_score, 6),
            "risk_level": risk_level,
            "model_version": model_version,
            "model_versions": risk_payload.get("model_versions") or {},
            "top_model_type": risk_payload.get("top_model_type"),
            "source": source,
            "analysis": risk_payload.get("analysis"),
            "drivers": factors,
            "factors": factors,
            "cards": risk_payload.get("cards") or [],
            "recommendations": risk_payload.get("recommendations") or [],
            "risks": risk_payload.get("risks") or {},
            "feature_snapshot": feature_payload,
            "data_availability": data_availability if isinstance(data_availability, dict) else {},
            "health_score": float(health_score_record.score),
            "health_components": {
                "risk_component": float(health_score_record.risk_component) if health_score_record.risk_component is not None else None,
                "lifestyle_component": float(health_score_record.lifestyle_component) if health_score_record.lifestyle_component is not None else None,
                "vitals_component": float(health_score_record.vitals_component) if health_score_record.vitals_component is not None else None,
                "sleep_component": float(health_score_record.sleep_component) if health_score_record.sleep_component is not None else None,
            },
            "confidence": risk_payload.get("confidence"),
            "data_points": risk_payload.get("data_points"),
            "last_updated": health_score_record.calculated_at.isoformat() if health_score_record.calculated_at else datetime.now(timezone.utc).isoformat(),
        }
        risks = data["risks"] if isinstance(data["risks"], dict) else {}
        data["diabetes_risk"] = _risk_value(risks, "diabetes_risk", "diabetes")
        data["cardio_risk"] = _risk_value(risks, "cardio_risk", "cardiovascular")
        data["sleep_risk"] = _risk_value(risks, "sleep_risk", "sleep")
        return {
            "success": True,
            "status": "ready",
            "source": source,
            "error": None,
            "data": data,
            "last_updated": data["last_updated"],
        }

    @staticmethod
    def _feature_snapshot_payload(feature_snapshot: Any) -> dict[str, Any]:
        if isinstance(feature_snapshot, FeatureSnapshotRecord):
            if isinstance(feature_snapshot.feature_payload, dict) and feature_snapshot.feature_payload:
                payload = dict(feature_snapshot.feature_payload)
                payload.setdefault("hr_mean_7d", float(feature_snapshot.hr_mean_7d) if feature_snapshot.hr_mean_7d is not None else 0.0)
                payload.setdefault("steps_avg_7d", float(feature_snapshot.steps_avg_7d) if feature_snapshot.steps_avg_7d is not None else 0.0)
                payload.setdefault("sleep_efficiency", float(feature_snapshot.sleep_efficiency) if feature_snapshot.sleep_efficiency is not None else 0.0)
                payload.setdefault("heart_rate", payload.get("hr_mean_7d"))
                payload.setdefault("steps", payload.get("steps_avg_7d"))
                payload.setdefault("sleep_hours", payload.get("sleep_duration") or payload.get("sleep"))
                if not isinstance(payload.get("data_availability"), dict):
                    payload["data_availability"] = {"steps": False, "heart_rate": False, "sleep": False}
                return payload
            return {
                "snapshot_id": str(feature_snapshot.id),
                "bmi": float(feature_snapshot.bmi) if feature_snapshot.bmi is not None else None,
                "hr_mean_7d": float(feature_snapshot.hr_mean_7d) if feature_snapshot.hr_mean_7d is not None else 0.0,
                "steps_avg_7d": float(feature_snapshot.steps_avg_7d) if feature_snapshot.steps_avg_7d is not None else 0.0,
                "sleep_efficiency": float(feature_snapshot.sleep_efficiency) if feature_snapshot.sleep_efficiency is not None else 0.0,
                "heart_rate": float(feature_snapshot.hr_mean_7d) if feature_snapshot.hr_mean_7d is not None else 0.0,
                "steps": float(feature_snapshot.steps_avg_7d) if feature_snapshot.steps_avg_7d is not None else 0.0,
                "sleep_hours": 0.0,
                "lifestyle_score": float(feature_snapshot.lifestyle_score) if feature_snapshot.lifestyle_score is not None else None,
                "activity_score": float(feature_snapshot.activity_score) if feature_snapshot.activity_score is not None else None,
                "confidence": float(feature_snapshot.confidence) if feature_snapshot.confidence is not None else None,
                "data_availability": {"steps": False, "heart_rate": False, "sleep": False},
            }
        if hasattr(feature_snapshot, "to_dict"):
            return feature_snapshot.to_dict()
        if isinstance(feature_snapshot, dict):
            return dict(feature_snapshot)
        return {}

    @staticmethod
    def _resolve_snapshot_record(db: Session, user: User, feature_snapshot: Any) -> FeatureSnapshotRecord | None:
        if isinstance(feature_snapshot, FeatureSnapshotRecord):
            return feature_snapshot

        snapshot_id = getattr(feature_snapshot, "snapshot_id", None)
        if snapshot_id is None and isinstance(feature_snapshot, dict):
            snapshot_id = feature_snapshot.get("snapshot_id")

        if snapshot_id is not None:
            record = (
                db.query(FeatureSnapshotRecord)
                .filter(
                    FeatureSnapshotRecord.id == snapshot_id,
                    FeatureSnapshotRecord.user_id == user.id,
                )
                .one_or_none()
            )
            if record is not None:
                return record

        return None

    @staticmethod
    def _build_risk_payload(
        *,
        prediction_probability: float,
        confidence: float,
        model_version: str | None,
        feature_snapshot_record: FeatureSnapshotRecord,
        condition_scores: dict[str, float] | None = None,
        model_versions: dict[str, str | None] | None = None,
        top_model_type: str = "diabetes",
    ) -> dict[str, Any]:
        risk_level = _risk_level(prediction_probability)
        feature_snapshot_payload = MLPipelineService._feature_snapshot_payload(feature_snapshot_record)
        normalized_condition_scores = condition_scores or {"diabetes": float(prediction_probability)}
        risk_scores = {
            _risk_key(model_type): float(score)
            for model_type, score in normalized_condition_scores.items()
        }
        risk_scores.update(
            {
                _condition_risk_key(model_type): float(score)
                for model_type, score in normalized_condition_scores.items()
            }
        )
        risk_scores["overall_risk_score"] = float(prediction_probability)
        risk_scores["risk_level"] = risk_level
        cards = [
            {
                "key": _risk_key(model_type),
                "label": _risk_label(model_type),
                "score": round(float(score) * 100.0, 2),
                "risk_level": _risk_level(float(score)),
                "model_version": (model_versions or {}).get(model_type),
            }
            for model_type, score in normalized_condition_scores.items()
        ]
        cards.sort(key=lambda item: float(item["score"]), reverse=True)
        return {
            "overall_score": float(prediction_probability),
            "risk_score": float(prediction_probability),
            "risk_level": risk_level,
            "confidence": float(prediction_probability),
            "confidence_label": _risk_level(float(prediction_probability)),
            "model_version": model_version,
            "model_versions": model_versions or {},
            "top_model_type": _risk_key(top_model_type),
            "analysis": "Calibrated XGBoost disease-specific inference completed successfully.",
            "recommendations": [],
            "drivers": [],
            "cards": cards,
            "feature_snapshot": feature_snapshot_payload,
            "feature_snapshot_id": str(feature_snapshot_record.id),
            "risks": risk_scores,
        }

    @staticmethod
    def _persist_risk_context(
        db: Session,
        user: User,
        *,
        feature_snapshot_record: FeatureSnapshotRecord,
        risk_payload: dict[str, Any],
        report_id: str | None = None,
        run_id: str | None = None,
    ) -> tuple[Any, Any]:
        risk_score_record = StoragePipelineService.store_risk_score(
            db,
            user,
            risk_payload=risk_payload,
            feature_snapshot_id=feature_snapshot_record.id,
            report_id=report_id or feature_snapshot_record.report_id,
            model_version=risk_payload.get("model_version"),
            source="ml",
            status="ready",
            run_id=run_id,
        )

        from ai.scoring.realtime.event_listener import ScoringEventListener

        health_score_record, scoring_payload = ScoringEventListener.on_prediction_change(
            db,
            user,
            risk_score=risk_score_record,
            feature_snapshot=feature_snapshot_record,
        )
        enriched_risk_payload = dict(risk_score_record.risk_payload or {})
        enriched_risk_payload["health_score"] = float(scoring_payload.get("score") or 0.0)
        enriched_risk_payload["health_intelligence"] = {
            "trend": scoring_payload.get("trend"),
            "confidence": scoring_payload.get("confidence"),
            "volatility": scoring_payload.get("volatility"),
            "baseline_delta": scoring_payload.get("baseline_delta"),
            "anomaly_level": scoring_payload.get("anomaly_level"),
            "explanation": scoring_payload.get("explanation"),
        }
        risk_score_record.risk_payload = enriched_risk_payload
        risk_score_record.health_score = float(scoring_payload.get("score") or 0.0)
        db.add(risk_score_record)
        db.commit()
        db.refresh(risk_score_record)
        return risk_score_record, health_score_record

    @staticmethod
    def _persist_shap_values(
        db: Session,
        user: User,
        *,
        feature_snapshot_record: FeatureSnapshotRecord,
        risk_score_record: Any,
        risk_payload: dict[str, Any],
        loaded_model: Any,
        features: list[float],
    ) -> list[dict[str, Any]]:
        shap_entries = ShapExplainer.explain(
            feature_snapshot_record,
            loaded_model=loaded_model,
            features=features,
        )
        StoragePipelineService.store_shap_values(
            db,
            user,
            risk_score=risk_score_record,
            shap_entries=shap_entries,
            source_type="ml",
        )
        risk_score_record.risk_payload = {
            **(risk_score_record.risk_payload or risk_payload),
            "drivers": shap_entries,
        }
        db.commit()
        db.refresh(risk_score_record)
        return shap_entries

    @staticmethod
    def run_latest_snapshot_prediction(db: Session, user: User) -> dict[str, Any]:
        snapshot_record = StoragePipelineService.latest_feature_snapshot(db, user)
        if snapshot_record is None:
            raise ValueError("No feature snapshot available for this user.")
        return MLPipelineService.predict_from_snapshot_record(db, user, snapshot_record)

    @staticmethod
    def predict(db: Session, user: User, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        overrides = MLPipelineService._prepare_feature_overrides(payload)
        feature_snapshot = FeaturePipelineService.build_feature_snapshot(
            db,
            user,
            overrides=overrides,
            persist=True,
            report_id=(payload or {}).get("report_id"),
        )

        snapshot_record = MLPipelineService._resolve_snapshot_record(db, user, feature_snapshot)
        if snapshot_record is None:
            raise RuntimeError("Persisted feature snapshot could not be resolved for prediction.")

        return MLPipelineService.predict_from_snapshot_record(
            db,
            user,
            snapshot_record,
            payload=payload,
            report_id=(payload or {}).get("report_id"),
        )

    @staticmethod
    def predict_from_snapshot(
        db: Session,
        user: User,
        feature_snapshot: Any,
        *,
        payload: dict[str, Any] | None = None,
        report_id: str | None = None,
    ) -> dict[str, Any]:
        snapshot_record = MLPipelineService._resolve_snapshot_record(db, user, feature_snapshot)
        if snapshot_record is None:
            if isinstance(feature_snapshot, dict):
                feature_snapshot = FeatureSnapshot.from_dict(feature_snapshot)
            feature_snapshot = FeaturePipelineService.build_feature_snapshot(
                db,
                user,
                overrides=MLPipelineService._feature_snapshot_payload(feature_snapshot),
                persist=True,
                report_id=report_id,
            )
            snapshot_record = MLPipelineService._resolve_snapshot_record(db, user, feature_snapshot)
            if snapshot_record is None:
                raise RuntimeError("Persisted feature snapshot could not be resolved for prediction.")

        return MLPipelineService.predict_from_snapshot_record(
            db,
            user,
            snapshot_record,
            payload=payload,
            report_id=report_id,
        )

    @staticmethod
    def predict_from_snapshot_record(
        db: Session,
        user: User,
        feature_snapshot_record: FeatureSnapshotRecord,
        *,
        payload: dict[str, Any] | None = None,
        report_id: str | None = None,
    ) -> dict[str, Any]:
        loaded_models = ModelLoader.load_all(strict=True)
        if not loaded_models:
            raise RuntimeError("ML models could not be loaded.")

        feature_payload = MLPipelineService._feature_snapshot_payload(feature_snapshot_record)
        inference_results: dict[str, Any] = {}
        condition_scores: dict[str, float] = {}
        for model_type, loaded_model in loaded_models.items():
            inference = MLPipelineInference(loaded_model)
            result = inference.predict(feature_payload)
            if result is None:
                logger.warning("ML inference failed for model_type=%s user=%s", model_type, user.id)
                continue
            inference_results[model_type] = result
            condition_scores[model_type] = float(result.score)

        if not condition_scores:
            raise RuntimeError("ML inference failed for the latest feature snapshot.")

        top_model_type = max(condition_scores, key=condition_scores.get)
        loaded_model = loaded_models[top_model_type]
        inference_result = inference_results[top_model_type]

        confidence = float(inference_result.score)
        features = build_feature_vector(feature_payload, loaded_model.feature_names)
        model_versions = {
            model_type: inference_results[model_type].model_version
            for model_type in inference_results
        }
        risk_payload = MLPipelineService._build_risk_payload(
            prediction_probability=inference_result.score,
            confidence=confidence,
            model_version=inference_result.model_version,
            feature_snapshot_record=feature_snapshot_record,
            condition_scores=condition_scores,
            model_versions=model_versions,
            top_model_type=top_model_type,
        )
        risk_payload["data_points"] = feature_snapshot_record.feature_payload.get("data_points") if isinstance(feature_snapshot_record.feature_payload, dict) else None

        risk_score_record, health_score_record = MLPipelineService._persist_risk_context(
            db,
            user,
            feature_snapshot_record=feature_snapshot_record,
            risk_payload=risk_payload,
            report_id=report_id,
            run_id=(payload or {}).get("run_id"),
        )
        generate_health_alerts(user.id, db)

        factors: list[dict[str, Any]] = []
        try:
            factors = MLPipelineService._persist_shap_values(
                db,
                user,
                feature_snapshot_record=feature_snapshot_record,
                risk_score_record=risk_score_record,
                risk_payload=risk_payload,
                loaded_model=loaded_model,
                features=features,
            )
        except Exception as exc:
            db.rollback()
            logger.exception(
                "SHAP explanation failed for user=%s prediction=%s: %s",
                user.id,
                risk_score_record.id,
                exc,
            )

        response = MLPipelineService._compose_response(
            user=user,
            feature_snapshot=feature_snapshot_record,
            risk_payload=risk_payload,
            risk_score_record=risk_score_record,
            health_score_record=health_score_record,
            model_version=inference_result.model_version,
            source="ml",
            factors=factors,
        )
        try:
            from services.prediction_explanation_service import PredictionExplanationService

            response = PredictionExplanationService.hydrate_prediction_response_sync(
                db,
                user,
                response,
                prediction_id=str(risk_score_record.id),
            )
        except Exception as exc:
            logger.exception(
                "RAG explanation hydration failed for user=%s prediction=%s: %s",
                user.id,
                risk_score_record.id,
                exc,
            )
        try:
            from services.notification_service import trigger_notification_sync

            explanation = (response.get("data") or {}).get("explanation") or {}
            trigger_notification_sync(
                user_id=str(user.id),
                event_type="ai_insight",
                title="AI Insight Ready",
                message="Your health risk analysis is available.",
                data={
                    "prediction_id": str(risk_score_record.id),
                    "risk_score": (response.get("data") or {}).get("risk_score"),
                    "risk_level": (response.get("data") or {}).get("risk_level"),
                    "summary": explanation.get("summary") or (response.get("data") or {}).get("analysis"),
                    "url": "/insights",
                },
            )
        except Exception as exc:
            logger.exception(
                "AI insight notification emission failed for user=%s prediction=%s: %s",
                user.id,
                risk_score_record.id,
                exc,
            )
        return response
