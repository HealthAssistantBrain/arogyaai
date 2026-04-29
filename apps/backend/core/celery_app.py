from __future__ import annotations

import os
from types import SimpleNamespace
from uuid import uuid4

try:
    from celery import Celery

    CELERY_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - local test fallback
    Celery = None
    CELERY_AVAILABLE = False


class _FallbackConf:
    def update(self, **kwargs):
        return None


class _FallbackResult:
    def __init__(self, task_id: str, state: str, result=None):
        self.id = task_id
        self.state = state
        self.result = result

    def ready(self) -> bool:
        return self.state in {"SUCCESS", "FAILURE"}

    def successful(self) -> bool:
        return self.state == "SUCCESS"

    def failed(self) -> bool:
        return self.state == "FAILURE"


class _FallbackTask:
    def __init__(self, app, func, *, bind: bool = False):
        self._app = app
        self._func = func
        self._bind = bind

    def delay(self, *args, **kwargs):
        task_id = str(uuid4())
        call_args = args
        if self._bind:
            call_args = (SimpleNamespace(request=None), *args)

        try:
            result = self._func(*call_args, **kwargs)
            payload = _FallbackResult(task_id, "SUCCESS", result)
        except Exception as exc:  # pragma: no cover - only used without Celery installed
            payload = _FallbackResult(task_id, "FAILURE", exc)

        self._app.results[task_id] = payload
        return payload

    def apply_async(self, args=None, kwargs=None):
        return self.delay(*(args or ()), **(kwargs or {}))

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)


class _FallbackCeleryApp:
    def __init__(self) -> None:
        self.conf = _FallbackConf()
        self.results: dict[str, _FallbackResult] = {}

    def task(self, *args, **kwargs):
        bind = bool(kwargs.get("bind"))

        def decorator(func):
            return _FallbackTask(self, func, bind=bind)

        return decorator


CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0").strip()
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1").strip()

if CELERY_AVAILABLE:
    celery_app = Celery(
        "arogyaai",
        broker=CELERY_BROKER_URL,
        backend=CELERY_RESULT_BACKEND,
        include=["pipelines.tasks", "pipelines.orchestration_pipeline.tasks"],
    )
else:  # pragma: no cover - local test fallback
    celery_app = _FallbackCeleryApp()

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)
