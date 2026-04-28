from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from pipelines.storage_pipeline.service import StoragePipelineService
from pipelines.storage_pipeline.utils import serialize_for_json


def _mock_db(existing_record=None) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = existing_record
    return db


def test_serialize_for_json_converts_nested_datetimes():
    now = datetime.now(timezone.utc)
    payload = {
        "window_start": now,
        "metric_payload": {
            "generated_at": now,
            "history": [{"captured_at": now}],
        },
    }

    serialized = serialize_for_json(payload)

    assert serialized["window_start"] == now.isoformat()
    assert serialized["metric_payload"]["generated_at"] == now.isoformat()
    assert serialized["metric_payload"]["history"][0]["captured_at"] == now.isoformat()


def test_store_baseline_metrics_serializes_json_payload_and_preserves_datetime_columns():
    db = _mock_db()
    user = SimpleNamespace(id=uuid4())
    now = datetime.now(timezone.utc)

    persisted = StoragePipelineService.store_baseline_metrics(
        db,
        user,
        [
            {
                "metric_name": "health_score_baseline",
                "mean_7d": 82.5,
                "mean_30d": 82.5,
                "std_dev": 0,
                "sample_count": 1,
                "window_start": now,
                "window_end": now,
                "metric_payload": {
                    "source": "onboarding_completion",
                    "generated_at": now,
                },
            }
        ],
    )

    record = persisted[0]

    assert record.window_start == now
    assert record.window_end == now
    assert record.metric_payload["window_start"] == now.isoformat()
    assert record.metric_payload["window_end"] == now.isoformat()
    assert record.metric_payload["metric_payload"]["generated_at"] == now.isoformat()
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_store_baseline_metrics_rolls_back_when_commit_fails():
    db = _mock_db()
    db.commit.side_effect = RuntimeError("commit failed")
    user = SimpleNamespace(id=uuid4())
    now = datetime.now(timezone.utc)

    with pytest.raises(RuntimeError, match="commit failed"):
        StoragePipelineService.store_baseline_metrics(
            db,
            user,
            [
                {
                    "metric_name": "risk_score_baseline",
                    "window_start": now,
                    "window_end": now,
                }
            ],
        )

    db.rollback.assert_called_once()
