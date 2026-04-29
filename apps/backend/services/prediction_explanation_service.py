from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from models import RiskScore, ShapValueRecord, User
from pipelines.rag_pipeline import RagExplanationPipeline
from pipelines.storage_pipeline.service import StoragePipelineService


class PredictionExplanationService:
    @staticmethod
    def _risk_record(
        db: Session,
        user: User,
        prediction_id: str | None = None,
    ) -> RiskScore | None:
        if prediction_id:
            return (
                db.query(RiskScore)
                .filter(RiskScore.id == prediction_id, RiskScore.user_id == user.id)
                .one_or_none()
            )
        return StoragePipelineService.latest_risk_score(db, user)

    @staticmethod
    def _normalize_shap_rows(rows: list[ShapValueRecord]) -> list[dict[str, Any]]:
        normalized = []
        for row in rows:
            feature_value = None
            if isinstance(row.shap_payload, dict):
                raw_value = row.shap_payload.get("feature_value")
                try:
                    feature_value = None if raw_value is None else float(raw_value)
                except (TypeError, ValueError):
                    feature_value = None

            normalized.append(
                {
                    "feature_name": row.feature_name,
                    "shap_value": float(row.shap_value),
                    "abs_shap_value": float(row.abs_shap_value),
                    "direction": row.direction,
                    "feature_value": feature_value,
                    "shap_payload": row.shap_payload if isinstance(row.shap_payload, dict) else {},
                }
            )
        normalized.sort(key=lambda item: float(item.get("abs_shap_value") or 0.0), reverse=True)
        return normalized

    @staticmethod
    def _fallback_shap_payload(risk_score: RiskScore) -> list[dict[str, Any]]:
        payload = risk_score.risk_payload if isinstance(risk_score.risk_payload, dict) else {}
        drivers = payload.get("drivers")
        if not isinstance(drivers, list):
            return []
        normalized = []
        for item in drivers:
            if not isinstance(item, dict):
                continue
            try:
                shap_value = float(item.get("shap_value") or item.get("value") or item.get("contribution"))
            except (TypeError, ValueError):
                continue
            normalized.append(
                {
                    "feature_name": str(item.get("feature_name") or item.get("feature") or item.get("key") or ""),
                    "shap_value": shap_value,
                    "abs_shap_value": float(item.get("abs_shap_value") or abs(shap_value)),
                    "direction": str(item.get("direction") or ("increase" if shap_value >= 0 else "decrease")),
                    "feature_value": item.get("feature_value"),
                    "shap_payload": item,
                }
            )
        normalized.sort(key=lambda item: float(item.get("abs_shap_value") or 0.0), reverse=True)
        return normalized

    @staticmethod
    def _cache_key(risk_score: RiskScore, shap_values: list[dict[str, Any]]) -> str:
        cache_payload = {
            "prediction_id": str(risk_score.id),
            "overall_score": float(risk_score.overall_score) if risk_score.overall_score is not None else None,
            "risk_level": risk_score.risk_level.value if hasattr(risk_score.risk_level, "value") else str(risk_score.risk_level),
            "shap_values": [
                {
                    "feature_name": item.get("feature_name"),
                    "shap_value": round(float(item.get("shap_value") or 0.0), 6),
                    "abs_shap_value": round(float(item.get("abs_shap_value") or 0.0), 6),
                }
                for item in shap_values
            ],
        }
        return hashlib.sha256(json.dumps(cache_payload, sort_keys=True).encode("utf-8")).hexdigest()

    @staticmethod
    def _cached_explanation(risk_score: RiskScore, cache_key: str) -> dict[str, Any] | None:
        payload = risk_score.risk_payload if isinstance(risk_score.risk_payload, dict) else {}
        explanation = payload.get("rag_explanation")
        if not isinstance(explanation, dict):
            return None
        if explanation.get("cache_key") != cache_key:
            return None
        return explanation.get("payload") if isinstance(explanation.get("payload"), dict) else None

    @staticmethod
    def _store_cache(db: Session, risk_score: RiskScore, cache_key: str, explanation: dict[str, Any]) -> None:
        payload = dict(risk_score.risk_payload or {})
        payload["rag_explanation"] = {
            "cache_key": cache_key,
            "payload": explanation,
        }
        risk_score.risk_payload = payload
        db.commit()
        db.refresh(risk_score)

    @staticmethod
    def _attach_explanation(
        prediction_response: dict[str, Any],
        explanation: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not isinstance(prediction_response, dict):
            return prediction_response

        data = prediction_response.get("data")
        if not isinstance(data, dict):
            return prediction_response

        data["explanation"] = explanation if isinstance(explanation, dict) else None
        prediction_response["data"] = data
        return prediction_response

    @staticmethod
    async def hydrate_prediction_response(
        db: Session,
        user: User,
        prediction_response: dict[str, Any],
        *,
        prediction_id: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        data = prediction_response.get("data") if isinstance(prediction_response, dict) else None
        existing_explanation = data.get("explanation") if isinstance(data, dict) else None
        if isinstance(existing_explanation, dict) and not force_refresh:
            return prediction_response

        resolved_prediction_id = prediction_id or (data.get("prediction_id") if isinstance(data, dict) else None)
        explanation_response = await PredictionExplanationService.get_prediction_explanation(
            db,
            user,
            prediction_id=resolved_prediction_id,
            force_refresh=force_refresh,
        )
        explanation = explanation_response.get("data") if isinstance(explanation_response, dict) else None
        return PredictionExplanationService._attach_explanation(prediction_response, explanation if isinstance(explanation, dict) else None)

    @staticmethod
    def hydrate_prediction_response_sync(
        db: Session,
        user: User,
        prediction_response: dict[str, Any],
        *,
        prediction_id: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                PredictionExplanationService.hydrate_prediction_response(
                    db,
                    user,
                    prediction_response,
                    prediction_id=prediction_id,
                    force_refresh=force_refresh,
                )
            )
        return prediction_response

    @staticmethod
    async def get_prediction_explanation(
        db: Session,
        user: User,
        *,
        prediction_id: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        risk_score = PredictionExplanationService._risk_record(db, user, prediction_id=prediction_id)
        if risk_score is None:
            return {
                "success": False,
                "status": "fallback",
                "source": "db",
                "error": "No prediction was found for this user.",
                "data": None,
            }

        shap_rows = StoragePipelineService.latest_shap_values(db, risk_score.id)
        shap_values = (
            PredictionExplanationService._normalize_shap_rows(shap_rows)
            if shap_rows
            else PredictionExplanationService._fallback_shap_payload(risk_score)
        )
        if not shap_values:
            return {
                "success": False,
                "status": "fallback",
                "source": "db",
                "error": "No SHAP values were found for the selected prediction.",
                "data": {
                    "prediction_id": str(risk_score.id),
                    "risk_score": float(risk_score.overall_score) if risk_score.overall_score is not None else None,
                    "risk_level": risk_score.risk_level.value if hasattr(risk_score.risk_level, "value") else str(risk_score.risk_level),
                    "summary": "",
                    "factors": [],
                    "recommendations": [],
                    "sources": [],
                },
            }

        cache_key = PredictionExplanationService._cache_key(risk_score, shap_values)
        if not force_refresh:
            cached = PredictionExplanationService._cached_explanation(risk_score, cache_key)
            if cached is not None:
                return {
                    "success": True,
                    "status": "ready",
                    "source": "rag_cache",
                    "error": None,
                    "data": cached,
                }

        pipeline = RagExplanationPipeline()
        try:
            generated = await pipeline.explain(
                risk_score=float(risk_score.overall_score) if risk_score.overall_score is not None else 0.0,
                risk_level=risk_score.risk_level.value if hasattr(risk_score.risk_level, "value") else str(risk_score.risk_level),
                shap_values=shap_values,
            )
        except Exception as exc:
            return {
                "success": False,
                "status": "fallback",
                "source": "rag_pipeline",
                "error": str(exc),
                "data": {
                    "prediction_id": str(risk_score.id),
                    "risk_score": float(risk_score.overall_score) if risk_score.overall_score is not None else None,
                    "risk_level": risk_score.risk_level.value if hasattr(risk_score.risk_level, "value") else str(risk_score.risk_level),
                    "summary": "",
                    "factors": [],
                    "recommendations": [],
                    "sources": [],
                },
            }

        explanation = {
            "prediction_id": str(risk_score.id),
            "risk_score": float(risk_score.overall_score) if risk_score.overall_score is not None else None,
            "risk_percent": round((float(risk_score.overall_score) if risk_score.overall_score is not None else 0.0) * 100, 2),
            "risk_level": risk_score.risk_level.value if hasattr(risk_score.risk_level, "value") else str(risk_score.risk_level),
            "summary": generated.get("summary") or "",
            "factors": generated.get("factors") or [],
            "recommendations": generated.get("recommendations") or [],
            "sources": generated.get("sources") or [],
            "retrieval": generated.get("retrieval") or {},
            "top_features": generated.get("top_features") or [],
        }
        PredictionExplanationService._store_cache(db, risk_score, cache_key, explanation)
        return {
            "success": True,
            "status": "ready",
            "source": "rag_pipeline",
            "error": None,
            "data": explanation,
        }
