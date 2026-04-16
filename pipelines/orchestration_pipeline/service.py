from __future__ import annotations

from typing import Any

from pipelines.orchestration_pipeline.celery_app import CELERY_AVAILABLE, celery_app
from pipelines.orchestration_pipeline.tasks import OrchestrationTasks, _SYNC_RESULTS

if CELERY_AVAILABLE:
    from celery.result import AsyncResult
else:  # pragma: no cover - only used when Celery is unavailable locally
    AsyncResult = None


class OrchestrationPipelineService:
    @staticmethod
    def trigger_prediction(context: dict[str, Any]) -> dict[str, Any]:
        workflow = OrchestrationTasks.build_chain(context)
        result = workflow.apply_async()
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
        if not CELERY_AVAILABLE:
            sync_result = _SYNC_RESULTS.get(task_id)
            if sync_result is not None:
                return {
                    "success": True,
                    "status": "ready",
                    "source": "sync-fallback",
                    "error": None,
                    "data": {
                        "task_id": task_id,
                        "state": sync_result.state,
                        "ready": True,
                        "result": sync_result.result,
                    },
                }

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

        return {
            "success": True,
            "status": "processing",
            "source": "celery",
            "error": None,
            "data": payload,
        }
