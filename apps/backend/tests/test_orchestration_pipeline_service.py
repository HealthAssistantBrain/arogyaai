from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from pipelines.orchestration_pipeline.service import OrchestrationPipelineService
from pipelines.orchestration_pipeline.tasks import _SyncResult, compute_features


def test_trigger_prediction_enqueues_orchestration_chain():
    async_result = SimpleNamespace(id="chain-123", state="PENDING")
    chain = MagicMock()
    chain.apply_async.return_value = async_result

    with patch(
        "pipelines.orchestration_pipeline.service.OrchestrationTasks.build_chain",
        return_value=chain,
    ) as build_chain:
        result = OrchestrationPipelineService.trigger_prediction(
            {"user_id": "user-1", "payload": {"data_points": {"age": 29}}, "report_id": "report-9"}
        )

    build_chain.assert_called_once_with(
        {"user_id": "user-1", "payload": {"data_points": {"age": 29}}, "report_id": "report-9"}
    )
    chain.apply_async.assert_called_once_with()
    assert result == {
        "success": True,
        "status": "processing",
        "source": "celery",
        "error": None,
        "data": {"task_id": "chain-123", "state": "PENDING"},
    }


def test_get_status_reads_sync_fallback_results():
    task_id = "sync-123"
    sync_result = _SyncResult(
        id=task_id,
        state="SUCCESS",
        result={"prediction": {"risk_score": 0.42}},
    )
    fake_app = SimpleNamespace(results={task_id: sync_result})

    with patch("pipelines.orchestration_pipeline.service.CELERY_AVAILABLE", False), patch(
        "pipelines.orchestration_pipeline.service.celery_app",
        fake_app,
    ):
        result = OrchestrationPipelineService.get_status(task_id)

    assert result == {
        "success": True,
        "status": "ready",
        "source": "sync-fallback",
        "error": None,
        "data": {
            "task_id": task_id,
            "state": "SUCCESS",
            "ready": True,
            "result": {"prediction": {"risk_score": 0.42}},
        },
    }


def test_compute_features_preserves_report_id_in_context():
    db = MagicMock()
    user = SimpleNamespace(id="user-1")
    snapshot = MagicMock()
    snapshot.to_dict.return_value = {"steps": 6400}

    with patch("pipelines.orchestration_pipeline.tasks.SessionLocal", return_value=db), patch(
        "pipelines.orchestration_pipeline.tasks._load_user",
        return_value=user,
    ), patch(
        "pipelines.orchestration_pipeline.tasks.MLPipelineService._prepare_feature_overrides",
        return_value={"age": 29},
    ), patch(
        "pipelines.orchestration_pipeline.tasks.FeaturePipelineService.build_feature_snapshot",
        return_value=snapshot,
    ):
        result = compute_features(
            {
                "user_id": "user-1",
                "payload": {"data_points": {"age": 29}},
                "report_id": "report-9",
            }
        )

    assert result["user_id"] == "user-1"
    assert result["payload"] == {"data_points": {"age": 29}}
    assert result["feature_snapshot"] == {"steps": 6400}
    assert result["report_id"] == "report-9"
    db.close.assert_called_once_with()
