from __future__ import annotations

from typing import Any

try:
    from celery.result import AsyncResult
except ModuleNotFoundError:  # pragma: no cover - local test fallback
    AsyncResult = None

from core.celery_app import CELERY_AVAILABLE, celery_app
from pipelines.orchestration_pipeline.tasks import OrchestrationTasks


class OrchestrationPipelineService:
    @staticmethod
    def trigger_prediction(context: dict[str, Any]) -> dict[str, Any]:
        try:
            result = OrchestrationTasks.build_chain(context).apply_async()
        except Exception as exc:
            return {
                "success": False,
                "status": "fallback",
                "source": "celery",
                "error": f"Failed to enqueue pipeline: {exc}",
                "data": {
                    "task_id": None,
                    "state": "FAILED",
                },
            }

        return {
            "success": True,
            "status": "processing",
            "source": "celery",
            "error": None,
            "data": {
                "task_id": result.id,
                "state": result.state,
            },
        }

    @staticmethod
    def get_status(task_id: str) -> dict[str, Any]:
        if not CELERY_AVAILABLE or AsyncResult is None:
            result = getattr(celery_app, "results", {}).get(task_id)
            if result is None:
                return {
                    "success": True,
                    "status": "processing",
                    "source": "sync-fallback",
                    "error": None,
                    "data": {
                        "task_id": task_id,
                        "state": "PENDING",
                        "ready": False,
                    },
                }

            payload: dict[str, Any] = {
                "task_id": task_id,
                "state": result.state,
                "ready": result.ready(),
            }
            if result.successful():
                payload["result"] = result.result
                return {
                    "success": True,
                    "status": "ready",
                    "source": "sync-fallback",
                    "error": None,
                    "data": payload,
                }

            payload["error"] = str(result.result)
            return {
                "success": False,
                "status": "fallback",
                "source": "sync-fallback",
                "error": str(result.result),
                "data": payload,
            }

        result = AsyncResult(task_id, app=celery_app)
        payload: dict[str, Any] = {
            "task_id": task_id,
            "state": result.state,
            "ready": result.ready(),
        }

        if result.successful():
            payload["result"] = result.result
            return {
                "success": True,
                "status": "ready",
                "source": "celery",
                "error": None,
                "data": payload,
            }

        if result.failed():
            payload["error"] = str(result.result)
            return {
                "success": False,
                "status": "fallback",
                "source": "celery",
                "error": str(result.result),
                "data": payload,
            }

        if result.state == "RETRY":
            payload["retry"] = True

        return {
            "success": True,
            "status": "processing",
            "source": "celery",
            "error": None,
            "data": payload,
        }
