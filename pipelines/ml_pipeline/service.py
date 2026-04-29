from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy.orm import Session

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
    if score >= 0.75:
        return "CRITICAL"
    if score >= 0.50:
        return "HIGH"
    if score >= 0.25:
        return "MODERATE"
    return "LOW"


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
            "activity_level",
            "bmi",
            "systolic_bp",
            "diastolic_bp",
            "age",
            "cholesterol_proxy",
            "hr_mean_7d",
            "steps_avg_7d",
            "sleep_efficiency",
            "lifestyle_score",
            "activity_score",
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
            "source": source,
            "analysis": risk_payload.get("analysis"),
            "drivers": factors,
            "factors": factors,
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
                if not isinstance(payload.get("data_availability"), dict):
                    payload["data_availability"] = {"steps": False, "heart_rate": False, "sleep": False}
                return payload
            return {
                "snapshot_id": str(feature_snapshot.id),
                "bmi": float(feature_snapshot.bmi) if feature_snapshot.bmi is not None else None,
                "hr_mean_7d": float(feature_snapshot.hr_mean_7d) if feature_snapshot.hr_mean_7d is not None else 0.0,
                "steps_avg_7d": float(feature_snapshot.steps_avg_7d) if feature_snapshot.steps_avg_7d is not None else 0.0,
                "sleep_efficiency": float(feature_snapshot.sleep_efficiency) if feature_snapshot.sleep_efficiency is not None else 0.0,
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
    ) -> dict[str, Any]:
        risk_level = _risk_level(prediction_probability)
        feature_snapshot_payload = MLPipelineService._feature_snapshot_payload(feature_snapshot_record)
        return {
            "overall_score": float(prediction_probability),
            "risk_score": float(prediction_probability),
            "risk_level": risk_level,
            "confidence": float(confidence),
            "model_version": model_version,
            "analysis": "RandomForestClassifier inference completed successfully.",
            "recommendations": [],
            "drivers": [],
            "feature_snapshot": feature_snapshot_payload,
            "feature_snapshot_id": str(feature_snapshot_record.id),
            "risks": {
                "overall_risk_score": float(prediction_probability),
                "risk_level": risk_level,
            },
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

        health_payload = MLPipelineService._compute_health_score(feature_snapshot_record, risk_payload)
        health_score_record = StoragePipelineService.store_health_score(
            db,
            user,
            risk_score=risk_score_record,
            health_payload=health_payload,
            source="ml",
        )
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
        loader = ModelLoader()
        loaded_model = loader.load()
        if loaded_model is None:
            raise RuntimeError("ML model could not be loaded.")

        inference = MLPipelineInference(loaded_model)
        inference_result = inference.predict(MLPipelineService._feature_snapshot_payload(feature_snapshot_record))
        if inference_result is None:
            raise RuntimeError("ML inference failed for the latest feature snapshot.")

        features = build_feature_vector(feature_snapshot_record, loaded_model.feature_names)
        risk_payload = MLPipelineService._build_risk_payload(
            prediction_probability=inference_result.score,
            confidence=inference_result.confidence or inference_result.score,
            model_version=inference_result.model_version,
            feature_snapshot_record=feature_snapshot_record,
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
        return response
