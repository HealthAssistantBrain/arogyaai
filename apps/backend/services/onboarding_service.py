from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy.orm import Session

from models import User
from pipelines.baseline_pipeline.service import BaselinePipelineService
from pipelines.feature_pipeline.service import FeaturePipelineService
from pipelines.ml_pipeline.service import MLPipelineService
from pipelines.storage_pipeline.service import StoragePipelineService
from services.user_service import UserService

logger = logging.getLogger("onboarding_service")


def _serialize_baseline_record(record) -> dict[str, Any]:
    return {
        "metric_name": record.metric_name,
        "mean_7d": float(record.mean_7d) if record.mean_7d is not None else None,
        "mean_30d": float(record.mean_30d) if record.mean_30d is not None else None,
        "std_dev": float(record.std_dev) if record.std_dev is not None else None,
        "sample_count": int(record.sample_count or 0),
        "calculated_at": record.calculated_at.isoformat() if record.calculated_at else None,
    }


class OnboardingService:
    @staticmethod
    def _pipeline_artifacts_exist(db: Session, user: User) -> bool:
        latest_feature = StoragePipelineService.latest_feature_snapshot(db, user)
        latest_risk = StoragePipelineService.latest_risk_score(db, user)
        latest_health = StoragePipelineService.latest_health_score(db, user)
        latest_baselines = StoragePipelineService.latest_baseline_metrics(db, user)
        return bool(latest_feature and latest_risk and latest_health and latest_baselines)

    @staticmethod
    def _build_feature_overrides(profile_data: dict[str, Any]) -> dict[str, Any]:
        overrides: dict[str, Any] = {}
        for key in ("age", "activity_level", "height_cm", "weight_kg"):
            value = profile_data.get(key)
            if value is not None:
                overrides[key] = value
        return overrides

    @staticmethod
    def _upsert_default_baselines(db: Session, user: User, feature_snapshot, prediction_payload: dict[str, Any]) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        baseline_metrics = [
            {
                "metric_name": "bmi_baseline",
                "mean_7d": getattr(feature_snapshot, "bmi", None),
                "mean_30d": getattr(feature_snapshot, "bmi", None),
                "std_dev": 0,
                "sample_count": 1 if getattr(feature_snapshot, "bmi", None) is not None else 0,
                "window_start": now,
                "window_end": now,
                "metric_payload": {"source": "onboarding_completion"},
            },
            {
                "metric_name": "activity_level_baseline",
                "mean_7d": getattr(feature_snapshot, "activity_level", None),
                "mean_30d": getattr(feature_snapshot, "activity_level", None),
                "std_dev": 0,
                "sample_count": 1 if getattr(feature_snapshot, "activity_level", None) is not None else 0,
                "window_start": now,
                "window_end": now,
                "metric_payload": {"source": "onboarding_completion"},
            },
            {
                "metric_name": "risk_score_baseline",
                "mean_7d": prediction_payload.get("risk_score"),
                "mean_30d": prediction_payload.get("risk_score"),
                "std_dev": 0,
                "sample_count": 1 if prediction_payload.get("risk_score") is not None else 0,
                "window_start": now,
                "window_end": now,
                "metric_payload": {"source": "onboarding_completion"},
            },
            {
                "metric_name": "health_score_baseline",
                "mean_7d": prediction_payload.get("health_score"),
                "mean_30d": prediction_payload.get("health_score"),
                "std_dev": 0,
                "sample_count": 1 if prediction_payload.get("health_score") is not None else 0,
                "window_start": now,
                "window_end": now,
                "metric_payload": {"source": "onboarding_completion"},
            },
        ]

        persisted = StoragePipelineService.store_baseline_metrics(db, user, baseline_metrics)
        return [_serialize_baseline_record(record) for record in persisted]

    @staticmethod
    def finalize_onboarding(db: Session, user: User, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        user.is_onboarding_done = True
        user.onboarding_step = 6
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        if user.is_onboarding_done and OnboardingService._pipeline_artifacts_exist(db, user):
            latest_health = StoragePipelineService.latest_health_score(db, user)
            latest_risk = StoragePipelineService.latest_risk_score(db, user)
            latest_baselines = StoragePipelineService.latest_baseline_metrics(db, user)
            return {
                "success": True,
                "status": "ready",
                "source": "db",
                "error": None,
                "data": {
                    "user": UserService.get_user_me(db, user).get("data"),
                    "onboarding_completed": True,
                    "pipelines_triggered": False,
                    "health_score": float(latest_health.score) if latest_health is not None else None,
                    "risk_score": float(latest_risk.overall_score) if latest_risk is not None else None,
                    "baseline_metrics": [_serialize_baseline_record(item) for item in latest_baselines],
                },
                "last_updated": latest_health.calculated_at.isoformat() if latest_health and latest_health.calculated_at else None,
            }

        profile_data = UserService.get_user_me(db, user).get("data", {})
        feature_overrides = OnboardingService._build_feature_overrides(profile_data)
        if payload.get("activity_level") is not None:
            feature_overrides["activity_level"] = payload.get("activity_level")
        if payload.get("age") is not None:
            feature_overrides["age"] = payload.get("age")

        try:
            feature_snapshot = FeaturePipelineService.build_feature_snapshot(
                db,
                user,
                overrides=feature_overrides,
                persist=True,
            )
            BaselinePipelineService.compute_baselines(db, user, feature_snapshot)

            prediction_result = MLPipelineService.predict_from_snapshot(
                db,
                user,
                feature_snapshot,
                payload={
                    "data_points": {
                        **feature_overrides,
                        "source": "onboarding_completion",
                    }
                },
            )

            prediction_payload = prediction_result.get("data", {})
            default_baselines = OnboardingService._upsert_default_baselines(db, user, feature_snapshot, prediction_payload)
            latest_health = StoragePipelineService.latest_health_score(db, user)
            latest_risk = StoragePipelineService.latest_risk_score(db, user)
            latest_baselines = StoragePipelineService.latest_baseline_metrics(db, user)

            serialized_baselines = [_serialize_baseline_record(item) for item in latest_baselines]
            if default_baselines:
                default_metric_names = {item["metric_name"] for item in serialized_baselines}
                for item in default_baselines:
                    if item["metric_name"] not in default_metric_names:
                        serialized_baselines.append(item)

            return {
                "success": True,
                "status": "ready",
                "source": "pipeline",
                "error": None,
                "data": {
                    "user": UserService.get_user_me(db, user).get("data"),
                    "onboarding_completed": True,
                    "pipelines_triggered": True,
                    "feature_snapshot": feature_snapshot.to_dict(),
                    "health_score": float(latest_health.score) if latest_health is not None else prediction_payload.get("health_score"),
                    "risk_score": float(latest_risk.overall_score) if latest_risk is not None else prediction_payload.get("risk_score"),
                    "baseline_metrics": serialized_baselines,
                    "prediction": prediction_payload,
                },
                "last_updated": latest_health.calculated_at.isoformat() if latest_health and latest_health.calculated_at else None,
            }
        except Exception as exc:
            logger.exception("Onboarding pipeline finalization failed for user=%s: %s", user.id, exc)
            latest_health = StoragePipelineService.latest_health_score(db, user)
            latest_risk = StoragePipelineService.latest_risk_score(db, user)
            latest_baselines = StoragePipelineService.latest_baseline_metrics(db, user)
            return {
                "success": True,
                "status": "fallback",
                "source": "db",
                "error": f"Pipeline execution deferred: {exc}",
                "data": {
                    "user": UserService.get_user_me(db, user).get("data"),
                    "onboarding_completed": True,
                    "pipelines_triggered": False,
                    "health_score": float(latest_health.score) if latest_health is not None else None,
                    "risk_score": float(latest_risk.overall_score) if latest_risk is not None else None,
                    "baseline_metrics": [_serialize_baseline_record(item) for item in latest_baselines],
                },
                "last_updated": latest_health.calculated_at.isoformat() if latest_health and latest_health.calculated_at else None,
            }
