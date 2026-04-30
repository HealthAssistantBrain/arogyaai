from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import sys
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from pipelines.ml_pipeline.service import MLPipelineService


def test_ml_prediction_triggers_notification_after_successful_prediction():
    user = SimpleNamespace(id=uuid4())
    db = MagicMock()
    snapshot_record = SimpleNamespace(
        id=uuid4(),
        report_id=None,
        feature_payload={"data_points": {"sleep": 7.2}},
    )
    loaded_model = SimpleNamespace(feature_names=["sleep"])
    inference_result = SimpleNamespace(score=0.61, confidence=0.89, model_version="rf-v1")
    risk_score_record = SimpleNamespace(id=uuid4())
    health_score_record = SimpleNamespace(
        score=84.2,
        risk_component=71.0,
        lifestyle_component=79.0,
        vitals_component=81.0,
        sleep_component=88.0,
        calculated_at=datetime(2026, 4, 30, 18, 0, tzinfo=timezone.utc),
    )
    base_response = {
        "data": {
            "prediction_id": str(risk_score_record.id),
            "risk_score": 0.61,
            "risk_level": "MODERATE",
            "analysis": "Risk analysis complete.",
        }
    }

    with patch("pipelines.ml_pipeline.service.ModelLoader.load", return_value=loaded_model), patch(
        "pipelines.ml_pipeline.service.MLPipelineInference.predict",
        return_value=inference_result,
    ), patch(
        "pipelines.ml_pipeline.service.build_feature_vector",
        return_value=[7.2],
    ), patch.object(
        MLPipelineService,
        "_build_risk_payload",
        return_value={"overall_score": 0.61, "risk_score": 0.61, "risk_level": "MODERATE", "analysis": "Risk analysis complete."},
    ), patch.object(
        MLPipelineService,
        "_persist_risk_context",
        return_value=(risk_score_record, health_score_record),
    ), patch(
        "pipelines.ml_pipeline.service.generate_health_alerts",
    ), patch.object(
        MLPipelineService,
        "_persist_shap_values",
        return_value=[],
    ), patch.object(
        MLPipelineService,
        "_compose_response",
        return_value=base_response,
    ), patch(
        "services.prediction_explanation_service.PredictionExplanationService.hydrate_prediction_response_sync",
        return_value={**base_response, "data": {**base_response["data"], "explanation": {"summary": "Your health risk analysis is available."}}},
    ), patch(
        "services.notification_service.trigger_notification_sync",
    ) as trigger_notification:
        result = MLPipelineService.predict_from_snapshot_record(db, user, snapshot_record)

    assert result["data"]["prediction_id"] == str(risk_score_record.id)
    trigger_notification.assert_called_once()
