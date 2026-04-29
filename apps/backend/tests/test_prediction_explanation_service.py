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
