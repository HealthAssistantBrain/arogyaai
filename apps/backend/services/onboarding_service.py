from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from models import User
from pipelines.contracts import PipelineContract
from pipelines.orchestration_pipeline.service import OrchestrationPipelineService
from pipelines.schemas import BaselineMetricDTO
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
        for key in ("age", "activity_level", "height_cm", "weight_kg", "sleep", "stress", "severity_score"):
            value = profile_data.get(key)
            if value is not None:
                overrides[key] = value
        if profile_data.get("sex") is not None:
            overrides["sex"] = profile_data.get("sex")
        if isinstance(profile_data.get("symptom_flags"), dict):
            overrides["symptom_flags"] = profile_data.get("symptom_flags")
        if isinstance(profile_data.get("disease_flags"), dict):
            overrides["disease_flags"] = profile_data.get("disease_flags")
        if isinstance(profile_data.get("family_history_flags"), dict):
            overrides["family_history_flags"] = profile_data.get("family_history_flags")
        return overrides

    @staticmethod
    def _extract_onboarding_payload(profile_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_profile": profile_data.get("user_profile") or {},
            "medical_history": profile_data.get("medical_history") or {},
            "lifestyle_profile": profile_data.get("lifestyle_profile") or {},
            "initial_clinical_snapshot": profile_data.get("initial_clinical_snapshot") or {},
            "device_connections": profile_data.get("device_connections") or {},
        }

    @staticmethod
    def _upsert_default_baselines(db: Session, user: User, feature_snapshot, prediction_payload: dict[str, Any]) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        baseline_metrics = [
            {
                "user_id": user.id,
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
                "user_id": user.id,
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
                "user_id": user.id,
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
                "user_id": user.id,
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

        try:
            validated_metrics = [BaselineMetricDTO.model_validate(metric) for metric in baseline_metrics]
        except ValidationError as exc:
            raise ValueError(f"Invalid ML output: {exc}") from exc

        PipelineContract.validate_baseline(validated_metrics)
        persisted = StoragePipelineService.store_baseline_metrics(db, user, validated_metrics)
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
            profile_data = UserService.get_user_me(db, user).get("data", {})
            return {
                "success": True,
                "status": "ready",
                "source": "db",
                "error": None,
                "data": {
                    "user": profile_data,
                    "onboarding_payload": OnboardingService._extract_onboarding_payload(profile_data),
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

        task_response = OrchestrationPipelineService.trigger_prediction(
            {
                "user_id": str(user.id),
                "payload": {
                    "data_points": {
                        **feature_overrides,
                        "source": "onboarding_completion",
                    }
                },
            }
        )

        if task_response.get("success"):
            task_data = task_response.get("data") or {}
            return {
                "success": True,
                "status": "processing",
                "source": task_response.get("source", "celery"),
                "error": None,
                "data": {
                    "user": profile_data,
                    "onboarding_payload": OnboardingService._extract_onboarding_payload(profile_data),
                    "onboarding_completed": True,
                    "pipelines_triggered": True,
                    "task_id": task_data.get("task_id"),
                    "task_state": task_data.get("state"),
                    "status_endpoint": f"/api/v1/prediction/status/{task_data['task_id']}" if task_data.get("task_id") else None,
                },
                "last_updated": None,
            }

        logger.error(
            "Onboarding pipeline enqueue failed for user=%s: %s",
            user.id,
            task_response.get("error"),
        )
        latest_health = StoragePipelineService.latest_health_score(db, user)
        latest_risk = StoragePipelineService.latest_risk_score(db, user)
        latest_baselines = StoragePipelineService.latest_baseline_metrics(db, user)
        return {
            "success": False,
            "status": "fallback",
            "source": task_response.get("source", "celery"),
            "error": task_response.get("error"),
            "data": {
                "user": profile_data,
                "onboarding_payload": OnboardingService._extract_onboarding_payload(profile_data),
                "onboarding_completed": True,
                "pipelines_triggered": False,
                "task_id": None,
                "health_score": float(latest_health.score) if latest_health is not None else None,
                "risk_score": float(latest_risk.overall_score) if latest_risk is not None else None,
                "baseline_metrics": [_serialize_baseline_record(item) for item in latest_baselines],
            },
            "last_updated": latest_health.calculated_at.isoformat() if latest_health and latest_health.calculated_at else None,
        }
