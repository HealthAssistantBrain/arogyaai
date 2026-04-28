from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock, patch
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from pipelines.schemas import BaselineMetricDTO
from services.onboarding_service import OnboardingService


def test_baseline_serialization():
    now = datetime.now(timezone.utc)
    data = {
        "user_id": uuid4(),
        "metric_name": "test",
        "mean_7d": 1.0,
        "mean_30d": 1.0,
        "std_dev": 0.0,
        "sample_count": 1,
        "window_start": now,
        "window_end": now,
        "metric_payload": {"time": now},
    }

    dto = BaselineMetricDTO.model_validate(data)
    dumped = dto.to_json_dict()

    assert isinstance(dumped, dict)
    assert dumped["window_start"] == now.isoformat()
    assert dumped["window_end"] == now.isoformat()
    assert dumped["metric_payload"]["time"] == now.isoformat()


def test_upsert_default_baselines_validates_metrics_before_storage():
    now = datetime.now(timezone.utc)
    user = SimpleNamespace(id=uuid4())
    feature_snapshot = SimpleNamespace(bmi=23.4, activity_level=7200)
    prediction_payload = {"risk_score": 31.2, "health_score": 78.9}
    fake_records: list[SimpleNamespace] = []

    def _fake_store(_db, _user, metrics):
        assert all(isinstance(metric, BaselineMetricDTO) for metric in metrics)
        for metric in metrics:
            fake_records.append(
                SimpleNamespace(
                    metric_name=metric.metric_name,
                    mean_7d=metric.mean_7d,
                    mean_30d=metric.mean_30d,
                    std_dev=metric.std_dev,
                    sample_count=metric.sample_count,
                    calculated_at=now,
                )
            )
        return fake_records

    with patch("services.onboarding_service.StoragePipelineService.store_baseline_metrics", side_effect=_fake_store):
        result = OnboardingService._upsert_default_baselines(
            MagicMock(),
            user,
            feature_snapshot,
            prediction_payload,
        )

    assert len(result) == 4
    assert {item["metric_name"] for item in result} == {
        "bmi_baseline",
        "activity_level_baseline",
        "risk_score_baseline",
        "health_score_baseline",
    }


def test_finalize_onboarding_enqueues_background_pipeline_when_artifacts_missing():
    user = SimpleNamespace(
        id=uuid4(),
        is_onboarding_done=False,
        onboarding_step=1,
        updated_at=None,
    )
    db = MagicMock()

    with patch("services.onboarding_service.OnboardingService._pipeline_artifacts_exist", return_value=False), patch(
        "services.onboarding_service.UserService.get_user_me",
        return_value={"data": {"age": 29, "activity_level": 4200}},
    ), patch(
        "services.onboarding_service.OrchestrationPipelineService.trigger_prediction",
        return_value={
            "success": True,
            "status": "processing",
            "source": "celery",
            "error": None,
            "data": {"task_id": "task-123", "state": "PENDING"},
        },
    ) as trigger_mock:
        result = OnboardingService.finalize_onboarding(
            db,
            user,
            {"activity_level": 6500},
        )

    db.commit.assert_called()
    db.refresh.assert_called_with(user)
    trigger_mock.assert_called_once_with(
        {
            "user_id": str(user.id),
            "payload": {
                "data_points": {
                    "age": 29,
                    "activity_level": 6500,
                    "source": "onboarding_completion",
                }
            },
        }
    )
    assert result["success"] is True
    assert result["status"] == "processing"
    assert result["data"]["task_id"] == "task-123"
    assert result["data"]["status_endpoint"] == "/api/v1/prediction/status/task-123"
