from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models import RiskScore, User
from pipelines.shap_pipeline.explainer import ShapExplainer
from pipelines.storage_pipeline.service import StoragePipelineService


class ShapPipelineService:
    @staticmethod
    def _serialize_rows(rows: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "feature_name": item.feature_name,
                "shap_value": float(item.shap_value),
                "abs_shap_value": float(item.abs_shap_value),
                "direction": item.direction,
                "explanation": item.explanation,
                "source_type": item.source_type,
                "calculated_at": item.calculated_at.isoformat() if item.calculated_at else None,
            }
            for item in rows
        ]

    @staticmethod
    def compute_shap(
        db: Session,
        user: User,
        risk_score: RiskScore,
        risk_payload: dict[str, Any],
        feature_snapshot: Any | None = None,
        model_available: bool = False,
    ) -> dict[str, Any]:
        existing_rows = StoragePipelineService.latest_shap_values(db, risk_score.id)
        has_model_rows = any(
            str(getattr(row, "source_type", "") or "").lower() in {"ml", "model"}
            for row in existing_rows
        )
        if existing_rows and (model_available or has_model_rows):
            return {
                "success": True,
                "status": "ready",
                "source": "model",
                "error": None,
                "data": {
                    "prediction_id": str(risk_score.id),
                    "values": ShapPipelineService._serialize_rows(existing_rows),
                    "feature_snapshot": feature_snapshot.to_dict() if hasattr(feature_snapshot, "to_dict") else feature_snapshot,
                },
            }

        shap_entries = ShapExplainer.fallback_entries(risk_payload)
        if not shap_entries and existing_rows:
            return {
                "success": True,
                "status": "ready",
                "source": "stored",
                "error": None,
                "data": {
                    "prediction_id": str(risk_score.id),
                    "values": ShapPipelineService._serialize_rows(existing_rows),
                    "feature_snapshot": feature_snapshot.to_dict() if hasattr(feature_snapshot, "to_dict") else feature_snapshot,
                },
            }

        persisted = StoragePipelineService.store_shap_values(
            db,
            user,
            risk_score=risk_score,
            shap_entries=shap_entries,
            source_type="model" if model_available else "rule_fallback",
        )

        return {
            "success": True,
            "status": "ready",
            "source": "model" if model_available else "rule_fallback",
            "error": None,
            "data": {
                "prediction_id": str(risk_score.id),
                "values": ShapPipelineService._serialize_rows(persisted),
                "feature_snapshot": feature_snapshot.to_dict() if hasattr(feature_snapshot, "to_dict") else feature_snapshot,
            },
        }
