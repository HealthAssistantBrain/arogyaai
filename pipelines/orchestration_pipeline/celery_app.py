from __future__ import annotations

import os

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - fallback for local/dev environments
    Celery = None
    CELERY_AVAILABLE = False


class _FallbackConf:
    def update(self, **kwargs):
        return None


class _FallbackCeleryApp:
    def __init__(self) -> None:
        self.conf = _FallbackConf()

    def task(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0")).strip()
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://redis:6379/0")).strip()

if CELERY_AVAILABLE:
    celery_app = Celery(
        "arogyaai_pipeline",
        broker=CELERY_BROKER_URL,
        backend=CELERY_RESULT_BACKEND,
        include=["pipelines.orchestration_pipeline.tasks"],
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        broker_connection_retry_on_startup=True,
        task_routes={
            "pipelines.orchestration_pipeline.tasks.compute_features": {"queue": "feature"},
            "pipelines.orchestration_pipeline.tasks.run_inference": {"queue": "ml"},
            "pipelines.orchestration_pipeline.tasks.compute_shap": {"queue": "shap"},
            "pipelines.orchestration_pipeline.tasks.compute_baseline": {"queue": "ingestion"},
        },
    )
else:
    celery_app = _FallbackCeleryApp()


class OrchestrationCeleryApp:
    celery = celery_app
