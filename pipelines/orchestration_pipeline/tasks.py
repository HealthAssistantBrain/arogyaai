from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from uuid import uuid4
from typing import Any

from database.session import SessionLocal
from models import RiskScore, User
from pipelines.baseline_pipeline.service import BaselinePipelineService
from pipelines.feature_pipeline.service import FeaturePipelineService, FeatureSnapshot
from pipelines.ml_pipeline.service import MLPipelineService
from pipelines.orchestration_pipeline.celery_app import CELERY_AVAILABLE, celery_app
from pipelines.shap_pipeline.service import ShapPipelineService
from pipelines.storage_pipeline.service import StoragePipelineService


def _load_user(db, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if user is None:
        raise LookupError(f"User {user_id} not found")
    return user


def _context_from_snapshot(snapshot: FeatureSnapshot, *, user_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "payload": payload or {},
        "feature_snapshot": snapshot.to_dict(),
    }


@dataclass
class _SyncResult:
    id: str
    state: str
    result: dict[str, Any]

    def ready(self) -> bool:
        return True


class _SyncChain:
    def __init__(self, context: dict[str, Any]):
        self._context = context
        self.id = str(uuid4())
        self.state = "PENDING"

    def apply_async(self) -> _SyncResult:
        context = dict(self._context)
        context = compute_features(context)
        context = run_inference(context)
        context = compute_shap(context)
        context = compute_baseline(context)
        result = _SyncResult(id=self.id, state="SUCCESS", result=context)
        _SYNC_RESULTS[self.id] = result
        self.state = result.state
        return result


_SYNC_RESULTS: dict[str, _SyncResult] = {}


if CELERY_AVAILABLE:
    task_decorator = celery_app.task
else:
    def task_decorator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


@task_decorator(name="pipelines.orchestration_pipeline.tasks.compute_features", queue="feature")
def compute_features(context: dict[str, Any]) -> dict[str, Any]:
    db = SessionLocal()
    try:
        user = _load_user(db, str(context["user_id"]))
        overrides = MLPipelineService._prepare_feature_overrides(context.get("payload"))
        snapshot = FeaturePipelineService.build_feature_snapshot(
            db,
            user,
            overrides=overrides,
            persist=True,
            report_id=context.get("report_id"),
        )
        return _context_from_snapshot(snapshot, user_id=str(user.id), payload=context.get("payload"))
    finally:
        db.close()


@task_decorator(name="pipelines.orchestration_pipeline.tasks.run_inference", queue="ml")
def run_inference(context: dict[str, Any]) -> dict[str, Any]:
    db = SessionLocal()
    try:
        user = _load_user(db, str(context["user_id"]))
        feature_snapshot = FeatureSnapshot.from_dict(context["feature_snapshot"])
        response = MLPipelineService.predict_from_snapshot(
            db,
            user,
            feature_snapshot,
            payload=context.get("payload"),
            report_id=context.get("report_id"),
        )
        context.update(
            {
                "prediction": response.get("data", {}),
            }
        )
        return context
    finally:
        db.close()


@task_decorator(name="pipelines.orchestration_pipeline.tasks.compute_shap", queue="shap")
def compute_shap(context: dict[str, Any]) -> dict[str, Any]:
    db = SessionLocal()
    try:
        user = _load_user(db, str(context["user_id"]))
        prediction_data = context.get("prediction") or {}
        prediction_id = prediction_data.get("prediction_id")
        if not prediction_id:
            return context

        risk_score = db.query(RiskScore).filter(RiskScore.id == prediction_id, RiskScore.user_id == user.id).first()
        if risk_score is None:
            return context

        feature_snapshot = FeatureSnapshot.from_dict(context["feature_snapshot"])
        shap_response = ShapPipelineService.compute_shap(
            db,
            user,
            risk_score,
            risk_score.risk_payload or prediction_data,
            feature_snapshot=feature_snapshot,
            model_available=(risk_score.prediction_source == "ml"),
        )
        context["shap"] = shap_response.get("data", {})
        return context
    finally:
        db.close()


@task_decorator(name="pipelines.orchestration_pipeline.tasks.compute_baseline", queue="ingestion")
def compute_baseline(context: dict[str, Any]) -> dict[str, Any]:
    db = SessionLocal()
    try:
        user = _load_user(db, str(context["user_id"]))
        feature_snapshot = FeatureSnapshot.from_dict(context["feature_snapshot"])
        baseline_response = BaselinePipelineService.compute_baselines(db, user, feature_snapshot)
        context["baseline"] = baseline_response.get("data", {})
        return context
    finally:
        db.close()


class OrchestrationTasks:
    compute_features = staticmethod(compute_features)
    run_inference = staticmethod(run_inference)
    compute_shap = staticmethod(compute_shap)
    compute_baseline = staticmethod(compute_baseline)

    @staticmethod
    def build_chain(context: dict[str, Any]):
        if CELERY_AVAILABLE:
            from celery import chain

            return chain(
                compute_features.s(context),
                run_inference.s(),
                compute_shap.s(),
                compute_baseline.s(),
            )

        return _SyncChain(context)
