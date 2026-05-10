from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from services.prediction_explanation_service import PredictionExplanationService
from models import RiskLevelEnum, RiskScore


def test_hydrate_prediction_response_embeds_generated_explanation():
    prediction_response = {
        "success": True,
        "status": "ready",
        "data": {
            "prediction_id": "prediction-1",
            "risk_score": 0.42,
        },
    }
    explanation_response = {
        "success": True,
        "status": "ready",
        "data": {
            "summary": "Hydrated explanation",
            "sources": [],
        },
    }

    with patch.object(
        PredictionExplanationService,
        "get_prediction_explanation",
        new=AsyncMock(return_value=explanation_response),
    ) as explanation_mock:
        result = asyncio.run(
            PredictionExplanationService.hydrate_prediction_response(
                MagicMock(),
                SimpleNamespace(id="user-1"),
                prediction_response,
            )
        )

    explanation_mock.assert_awaited_once()
    assert result["data"]["explanation"]["summary"] == "Hydrated explanation"


def test_hydrate_prediction_response_reuses_existing_embedded_explanation():
    prediction_response = {
        "success": True,
        "status": "ready",
        "data": {
            "prediction_id": "prediction-1",
            "explanation": {
                "summary": "Already present",
            },
        },
    }

    with patch.object(
        PredictionExplanationService,
        "get_prediction_explanation",
        new=AsyncMock(),
    ) as explanation_mock:
        result = asyncio.run(
            PredictionExplanationService.hydrate_prediction_response(
                MagicMock(),
                SimpleNamespace(id="user-1"),
                prediction_response,
            )
        )

    explanation_mock.assert_not_awaited()
    assert result["data"]["explanation"]["summary"] == "Already present"


def test_get_prediction_explanation_normalizes_generated_recommendations():
    risk_score = SimpleNamespace(
        id="prediction-1",
        overall_score=0.42,
        risk_level=SimpleNamespace(value="HIGH"),
        risk_payload={},
    )
    shap_rows = [
        SimpleNamespace(
            feature_name="activity",
            shap_value=0.21,
            abs_shap_value=0.21,
            direction="increase",
            shap_payload={"feature_value": 5200},
        )
    ]
    generated_payload = {
        "summary": "Generated summary",
        "factors": [],
        "recommendations": [
            {
                "title": "Increase Physical Activity",
                "detail": "Add more movement across the week.",
            }
        ],
        "sources": [],
        "retrieval": {},
        "top_features": [],
    }

    with patch.object(PredictionExplanationService, "_risk_record", return_value=risk_score), \
        patch("services.prediction_explanation_service.StoragePipelineService.latest_shap_values", return_value=shap_rows), \
        patch("services.prediction_explanation_service.RagExplanationPipeline") as pipeline_cls, \
        patch.object(PredictionExplanationService, "_store_cache", return_value=None):
        pipeline_cls.return_value.explain = AsyncMock(return_value=generated_payload)
        result = asyncio.run(
            PredictionExplanationService.get_prediction_explanation(
                MagicMock(),
                SimpleNamespace(id="user-1"),
            )
        )

    recommendation = result["data"]["recommendations"][0]
    assert recommendation["title"] == "Increase Physical Activity"
    assert recommendation["description"] == "Add more movement across the week."
    assert recommendation["category"] == "fitness"
    assert recommendation["priority"] == "high"


def test_get_prediction_explanation_builds_shap_fallback_recommendations():
    risk_score = SimpleNamespace(
        id="prediction-1",
        overall_score=0.42,
        risk_level=SimpleNamespace(value="HIGH"),
        risk_payload={},
    )
    shap_rows = [
        SimpleNamespace(
            feature_name="bmi",
            shap_value=0.24,
            abs_shap_value=0.24,
            direction="increase",
            shap_payload={"feature_value": 31.4},
        )
    ]
    generated_payload = {
        "summary": "Generated summary",
        "factors": [],
        "recommendations": [],
        "sources": [],
        "retrieval": {},
        "top_features": [],
    }

    with patch.object(PredictionExplanationService, "_risk_record", return_value=risk_score), \
        patch("services.prediction_explanation_service.StoragePipelineService.latest_shap_values", return_value=shap_rows), \
        patch("services.prediction_explanation_service.RagExplanationPipeline") as pipeline_cls, \
        patch.object(PredictionExplanationService, "_store_cache", return_value=None):
        pipeline_cls.return_value.explain = AsyncMock(return_value=generated_payload)
        result = asyncio.run(
            PredictionExplanationService.get_prediction_explanation(
                MagicMock(),
                SimpleNamespace(id="user-1"),
            )
        )

    recommendation = result["data"]["recommendations"][0]
    assert recommendation["category"] == "diet"
    assert recommendation["priority"] == "high"
    assert "BMI is currently 31.4" in recommendation["description"]


def test_get_prediction_explanation_can_defer_generation_to_background():
    risk_score = SimpleNamespace(
        id="prediction-1",
        overall_score=0.42,
        risk_level=SimpleNamespace(value="HIGH"),
        risk_payload={},
    )
    shap_rows = [
        SimpleNamespace(
            feature_name="activity",
            shap_value=0.21,
            abs_shap_value=0.21,
            direction="increase",
            shap_payload={"feature_value": 5200},
        )
    ]

    with patch.object(PredictionExplanationService, "_risk_record", return_value=risk_score), \
        patch("services.prediction_explanation_service.StoragePipelineService.latest_shap_values", return_value=shap_rows), \
        patch("services.prediction_explanation_service.ClinicalHistoryService.latest_history_analysis", return_value={}), \
        patch.object(PredictionExplanationService, "_cached_explanation", return_value=None):
        result = asyncio.run(
            PredictionExplanationService.get_prediction_explanation(
                MagicMock(),
                SimpleNamespace(id="user-1"),
                allow_generation=False,
            )
        )

    assert result["status"] == "processing"
    assert result["data"]["summary"] == "Personalized AI explanation is being prepared in the background."
    assert result["data"]["prediction_id"] == "prediction-1"


def test_get_prediction_explanation_adds_clinical_sections():
    risk_score = SimpleNamespace(
        id="prediction-1",
        overall_score=0.68,
        risk_level=SimpleNamespace(value="HIGH"),
        risk_payload={},
        feature_snapshot={
            "systolic_bp": 142,
            "diastolic_bp": 92,
            "activity_level": 4200,
            "sleep_duration": 5.8,
            "glucose": 108.0,
            "bmi": 31.4,
            "avg_rhr": 91,
        },
    )
    shap_rows = [
        SimpleNamespace(
            feature_name="activity",
            shap_value=0.21,
            abs_shap_value=0.21,
            direction="increase",
            shap_payload={"feature_value": 4200},
        )
    ]
    generated_payload = {
        "summary": "Generated summary",
        "factors": [],
        "recommendations": [],
        "sources": [],
        "retrieval": {},
        "top_features": [],
    }

    with patch.object(PredictionExplanationService, "_risk_record", return_value=risk_score), \
        patch("services.prediction_explanation_service.StoragePipelineService.latest_shap_values", return_value=shap_rows), \
        patch("services.prediction_explanation_service.RagExplanationPipeline") as pipeline_cls, \
        patch.object(PredictionExplanationService, "_store_cache", return_value=None):
        pipeline_cls.return_value.explain = AsyncMock(return_value=generated_payload)
        result = asyncio.run(
            PredictionExplanationService.get_prediction_explanation(
                MagicMock(),
                SimpleNamespace(id="user-1"),
            )
        )

    payload = result["data"]
    assert payload["risk_scores"]["cardiovascular"] > 0.68
    assert payload["outcome"]["severity"] == "high"
    assert "Hypertension risk" in payload["possible_conditions"]
    assert "Headache" in payload["symptoms"]
    assert payload["key_drivers"][0]["title"]


def test_get_prediction_explanation_merges_latest_clinical_history():
    risk_score = SimpleNamespace(
        id="prediction-1",
        overall_score=0.51,
        risk_level=SimpleNamespace(value="HIGH"),
        risk_payload={},
        feature_snapshot={
            "systolic_bp": 146,
            "diastolic_bp": 94,
            "activity_level": 5100,
            "sleep_duration": 6.1,
            "glucose": 104.0,
            "bmi": 28.4,
            "avg_rhr": 88,
        },
    )
    shap_rows = [
        SimpleNamespace(
            feature_name="blood_pressure",
            shap_value=0.18,
            abs_shap_value=0.18,
            direction="increase",
            shap_payload={"feature_value": 146},
        )
    ]
    generated_payload = {
        "summary": "Generated summary",
        "factors": [],
        "recommendations": [],
        "sources": [],
        "retrieval": {},
        "top_features": [],
    }
    latest_history = {
        "chief_complaint": "chest pain",
        "analysis": {
            "summary": "22-year-old user reports chest pain for 2 days but no cough or fever.",
            "symptoms": ["chest pain", "fatigue"],
            "possible_conditions": ["Cardiac risk"],
            "priority": "urgent",
            "recommendations": ["Prompt in-person clinical evaluation is advisable, especially if symptoms persist or worsen."],
            "ml_features": {
                "symptom_count": 2,
                "severity_score": 8,
                "system_flags": {"cardiovascular": True},
            },
            "rag_context": {
                "summary": "22-year-old user reports chest pain for 2 days but no cough or fever.",
            },
        },
    }

    with patch.object(PredictionExplanationService, "_risk_record", return_value=risk_score), \
        patch("services.prediction_explanation_service.StoragePipelineService.latest_shap_values", return_value=shap_rows), \
        patch("services.prediction_explanation_service.RagExplanationPipeline") as pipeline_cls, \
        patch("services.prediction_explanation_service.ClinicalHistoryService.latest_history_analysis", return_value=latest_history), \
        patch.object(PredictionExplanationService, "_store_cache", return_value=None):
        pipeline_cls.return_value.explain = AsyncMock(return_value=generated_payload)
        result = asyncio.run(
            PredictionExplanationService.get_prediction_explanation(
                MagicMock(),
                SimpleNamespace(id="user-1"),
            )
        )

    payload = result["data"]
    assert payload["clinical_history"]["chief_complaint"] == "chest pain"
    assert payload["clinical_features"]["symptom_count"] == 2
    assert payload["clinical_context"]["summary"].startswith("22-year-old user reports chest pain")
    assert "Cardiac risk" in payload["possible_conditions"]
    assert any(item["feature"] == "clinical_history" for item in payload["recommendations"])


def test_store_cache_persists_with_owned_session_scope():
    route_db = MagicMock()
    route_db.info = {"session_id": "session-123"}
    cache_db = MagicMock()
    attached_risk_score = SimpleNamespace(risk_payload={"existing": True})
    cache_db.get.return_value = attached_risk_score

    class _Scope:
        def __enter__(self):
            return ("primary", cache_db)

        def __exit__(self, exc_type, exc, tb):
            return False

    with patch.object(PredictionExplanationService, "_cache_write_scope", return_value=_Scope()), \
        patch.object(PredictionExplanationService, "_assert_active_session_entity", return_value=None), \
        patch("services.prediction_explanation_service.analytics_dual_write_enabled", return_value=False):
        PredictionExplanationService._store_cache(
            route_db,
            "prediction-1",
            "cache-key-1",
            {"summary": "Cached explanation"},
        )

    route_db.commit.assert_not_called()
    cache_db.get.assert_called_once()
    cache_db.commit.assert_called_once()
    assert attached_risk_score.risk_payload["existing"] is True
    assert attached_risk_score.risk_payload["rag_explanation"]["cache_key"] == "cache-key-1"


def test_store_cache_skips_detached_risk_score_instance():
    route_db = MagicMock()
    route_db.info = {"session_id": "session-detached"}
    detached_risk_score = RiskScore(
        id="prediction-1",
        user_id="user-1",
        risk_level=RiskLevelEnum.HIGH,
        overall_score=0.42,
    )

    PredictionExplanationService._store_cache(
        route_db,
        detached_risk_score,
        "cache-key-1",
        {"summary": "Cached explanation"},
    )

    route_db.commit.assert_not_called()


def test_get_prediction_explanation_returns_degraded_payload_on_service_error():
    risk_score = SimpleNamespace(
        id="prediction-1",
        overall_score=0.42,
        risk_level=SimpleNamespace(value="HIGH"),
        risk_payload={},
    )
    shap_rows = [
        SimpleNamespace(
            feature_name="activity",
            shap_value=0.21,
            abs_shap_value=0.21,
            direction="increase",
            shap_payload={"feature_value": 5200},
        )
    ]
    generated_payload = {
        "summary": "Generated summary",
        "factors": [],
        "recommendations": [],
        "sources": [],
        "retrieval": {},
        "top_features": [],
    }
    db = MagicMock()
    db.info = {"session_id": "session-degraded"}

    with patch.object(PredictionExplanationService, "_risk_record", return_value=risk_score), \
        patch("services.prediction_explanation_service.StoragePipelineService.latest_shap_values", return_value=shap_rows), \
        patch("services.prediction_explanation_service.RagExplanationPipeline") as pipeline_cls, \
        patch("services.prediction_explanation_service.ClinicalInsightService.enrich_payload", side_effect=RuntimeError("clinical payload broke")):
        pipeline_cls.return_value.explain = AsyncMock(return_value=generated_payload)
        result = asyncio.run(
            PredictionExplanationService.get_prediction_explanation(
                db,
                SimpleNamespace(id="user-1"),
            )
        )

    assert result["success"] is False
    assert result["status"] == "fallback"
    assert result["source"] == "service_degraded"
    assert result["data"]["prediction_id"] == "prediction-1"
    assert result["data"]["summary"]


def test_get_prediction_explanation_does_not_close_route_session():
    risk_score = SimpleNamespace(
        id="prediction-1",
        overall_score=0.42,
        risk_level=SimpleNamespace(value="HIGH"),
        risk_payload={},
    )
    shap_rows = [
        SimpleNamespace(
            feature_name="activity",
            shap_value=0.21,
            abs_shap_value=0.21,
            direction="increase",
            shap_payload={"feature_value": 5200},
        )
    ]
    generated_payload = {
        "summary": "Generated summary",
        "factors": [],
        "recommendations": [],
        "sources": [],
        "retrieval": {},
        "top_features": [],
    }
    db = MagicMock()
    db.info = {"session_id": "session-abc"}

    with patch.object(PredictionExplanationService, "_risk_record", return_value=risk_score), \
        patch("services.prediction_explanation_service.StoragePipelineService.latest_shap_values", return_value=shap_rows), \
        patch("services.prediction_explanation_service.RagExplanationPipeline") as pipeline_cls, \
        patch.object(PredictionExplanationService, "_store_cache", return_value=None):
        pipeline_cls.return_value.explain = AsyncMock(return_value=generated_payload)
        asyncio.run(
            PredictionExplanationService.get_prediction_explanation(
                db,
                SimpleNamespace(id="user-1"),
            )
        )

    db.close.assert_not_called()


def test_get_prediction_explanation_does_not_touch_risk_score_after_await():
    detached = False

    class _GuardedRiskScore:
        def __init__(self):
            self._id = "prediction-1"
            self._overall_score = 0.42
            self._risk_level = SimpleNamespace(value="HIGH")
            self._risk_payload = {"feature_snapshot": {"activity_level": 5200}}

        @property
        def id(self):
            if detached:
                raise AssertionError("RiskScore.id accessed after async boundary")
            return self._id

        @property
        def overall_score(self):
            if detached:
                raise AssertionError("RiskScore.overall_score accessed after async boundary")
            return self._overall_score

        @property
        def risk_level(self):
            if detached:
                raise AssertionError("RiskScore.risk_level accessed after async boundary")
            return self._risk_level

        @property
        def risk_payload(self):
            if detached:
                raise AssertionError("RiskScore.risk_payload accessed after async boundary")
            return self._risk_payload

        @property
        def feature_snapshot(self):
            if detached:
                raise AssertionError("RiskScore.feature_snapshot accessed after async boundary")
            return self._risk_payload["feature_snapshot"]

    async def _explain(**_kwargs):
        nonlocal detached
        detached = True
        return {
            "summary": "Generated summary",
            "factors": [],
            "recommendations": [],
            "sources": [],
            "retrieval": {},
            "top_features": [],
        }

    shap_rows = [
        SimpleNamespace(
            feature_name="activity",
            shap_value=0.21,
            abs_shap_value=0.21,
            direction="increase",
            shap_payload={"feature_value": 5200},
        )
    ]
    db = MagicMock()
    db.info = {"session_id": "session-guarded"}

    with patch.object(PredictionExplanationService, "_risk_record", return_value=_GuardedRiskScore()), \
        patch("services.prediction_explanation_service.StoragePipelineService.latest_shap_values", return_value=shap_rows), \
        patch("services.prediction_explanation_service.RagExplanationPipeline") as pipeline_cls, \
        patch.object(PredictionExplanationService, "_store_cache", return_value=None):
        pipeline_cls.return_value.explain = _explain
        result = asyncio.run(
            PredictionExplanationService.get_prediction_explanation(
                db,
                SimpleNamespace(id="user-1"),
            )
        )

    assert result["success"] is True
    assert result["data"]["prediction_id"] == "prediction-1"
