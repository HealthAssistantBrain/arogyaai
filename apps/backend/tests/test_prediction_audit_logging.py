from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from routes.prediction import run_prediction


def test_run_prediction_emits_audit_log_on_success():
    current_user = SimpleNamespace(id=uuid4())
    db = MagicMock()
    snapshot = SimpleNamespace(id=uuid4())

    with patch("routes.prediction.StoragePipelineService.latest_feature_snapshot", return_value=snapshot), patch(
        "routes.prediction.MLPipelineService.predict_from_snapshot_record",
        return_value={"data": {"prediction_id": "pred-1", "risk_score": 28.4, "factors": [{"name": "sleep"}]}},
    ), patch(
        "routes.prediction.PredictionExplanationService.hydrate_prediction_response",
        AsyncMock(return_value={"data": {"prediction_id": "pred-1", "risk_score": 28.4, "factors": [{"name": "sleep"}]}}),
    ), patch("routes.prediction.log_event") as log_event_mock:
        result = asyncio.run(run_prediction(current_user=current_user, db=db))

    assert result == {"risk_score": 28.4, "factors": [{"name": "sleep"}]}
    log_event_mock.assert_called_once_with(
        current_user.id,
        "prediction_run",
        "/api/v1/prediction/run",
        {
            "status": "success",
            "prediction_id": "pred-1",
            "risk_score": 28.4,
            "factor_count": 1,
            "feature_snapshot_id": snapshot.id,
        },
    )
