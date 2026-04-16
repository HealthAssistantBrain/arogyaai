from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from models import User
from pipelines.feature_pipeline.service import FeaturePipelineService, FeatureSnapshot
from pipelines.ml_pipeline.inference import MLPipelineInference
from pipelines.ml_pipeline.model_loader import ModelLoader
from pipelines.storage_pipeline.service import StoragePipelineService
from services.risk_engine import RiskEngine


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _risk_level(score: float) -> str:
    if score >= 65.0:
        return "CRITICAL"
    if score >= 45.0:
        return "HIGH"
    if score >= 25.0:
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
    ) -> dict[str, Any]:
        cards = risk_payload.get("cards") or []
        top_card = cards[0] if cards else {}
        overall_score = float(risk_payload.get("overall_score") or top_card.get("score") or 0.0)
        risk_level = str(risk_payload.get("risk_level") or top_card.get("risk_level") or _risk_level(overall_score)).upper()

        data = {
            "user_id": str(user.id),
            "prediction_id": str(risk_score_record.id),
            "health_score_id": str(health_score_record.id),
            "risk_score": round(overall_score, 2),
            "risk_level": risk_level,
            "model_version": model_version,
            "source": source,
            "analysis": risk_payload.get("analysis"),
            "drivers": risk_payload.get("drivers") or [],
            "recommendations": risk_payload.get("recommendations") or [],
            "risks": risk_payload.get("risks") or {},
            "feature_snapshot": feature_snapshot.to_dict() if hasattr(feature_snapshot, "to_dict") else feature_snapshot,
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
    def predict(db: Session, user: User, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        overrides = MLPipelineService._prepare_feature_overrides(payload)
        feature_snapshot = FeaturePipelineService.build_feature_snapshot(db, user, overrides=overrides, persist=True)

        return MLPipelineService.predict_from_snapshot(db, user, feature_snapshot, payload=payload)

    @staticmethod
    def predict_from_snapshot(
        db: Session,
        user: User,
        feature_snapshot: Any,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if isinstance(feature_snapshot, dict):
            feature_snapshot = FeatureSnapshot.from_dict(feature_snapshot)

        loader = ModelLoader()
        loaded_model = loader.load()
        inference = MLPipelineInference(loaded_model)
        inference_result = inference.predict(feature_snapshot.to_dict()) if inference.available else None

        if inference_result is not None:
            risk_payload = {
                "overall_score": inference_result.score,
                "risk_level": inference_result.risk_level,
                "confidence": inference_result.confidence,
                "cards": [
                    {
                        "key": "model_prediction",
                        "label": "Model Prediction",
                        "score": inference_result.score,
                        "risk_level": inference_result.risk_level,
                        "summary": "Prediction produced by the loaded model artifact.",
                    }
                ],
                "drivers": [],
                "recommendations": [],
                "risks": {
                    "overall_risk_score": inference_result.score,
                },
                "analysis": "Model-backed inference completed.",
                "data_points": getattr(feature_snapshot, "data_points", 0),
            }
            source = "ml"
            model_version = inference_result.model_version
        else:
            rule_payload = RiskEngine.evaluate(feature_snapshot, user_id=str(user.id))
            top_scores = [float(card.get("score") or 0.0) for card in rule_payload.get("risks", {}).get("cards", [])]
            overall_score = round(sum(top_scores) / len(top_scores), 2) if top_scores else 0.0
            risk_payload = {
                **rule_payload,
                "overall_score": overall_score,
                "risk_level": _risk_level(overall_score),
                "data_points": rule_payload.get("data_points") or getattr(feature_snapshot, "data_points", 0),
            }
            source = "rule_engine"
            model_version = None

        risk_score_record = StoragePipelineService.store_risk_score(
            db,
            user,
            risk_payload=risk_payload,
            feature_snapshot=feature_snapshot.to_dict(),
            model_version=model_version,
            source=source,
            status="ready",
        )

        health_payload = MLPipelineService._compute_health_score(feature_snapshot, risk_payload)
        health_score_record = StoragePipelineService.store_health_score(
            db,
            user,
            risk_score=risk_score_record,
            health_payload=health_payload,
            source=source,
        )

        return MLPipelineService._compose_response(
            user=user,
            feature_snapshot=feature_snapshot,
            risk_payload=risk_payload,
            risk_score_record=risk_score_record,
            health_score_record=health_score_record,
            model_version=model_version,
            source=source,
        )
