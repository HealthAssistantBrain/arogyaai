from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from database.session import get_db
from routes import symptoms as symptom_routes


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(symptom_routes.router)
    return app


def test_symptom_analyze_route_returns_session_payload():
    app = _build_app()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4())
    app.dependency_overrides[symptom_routes.get_current_user_from_header] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db

    expected = {
        "id": str(uuid4()),
        "analysis_status": "completed",
        "input": {"chief_complaint": "Headache"},
        "analysis": {"summary": "Symptoms suggest a non-specific pattern."},
        "timeline": {"saved_to_timeline": False},
    }

    with patch.object(symptom_routes.SymptomAnalysisService, "analyze", new=AsyncMock(return_value=expected)) as analyze_mock:
        response = TestClient(app).post(
            "/api/v1/symptoms/analyze",
            json={
                "chief_complaint": "Headache",
                "duration_value": 2,
                "duration_unit": "days",
                "severity": 4,
                "associated_symptoms": ["Fatigue"],
                "aggravating_factors": "",
                "relieving_factors": "",
                "previous_episodes": "",
                "medications": "",
                "notes": "",
            },
        )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == expected["id"]
    analyze_mock.assert_awaited_once()


def test_symptom_history_and_timeline_routes_share_service_contract():
    app = _build_app()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4())
    session_id = str(uuid4())
    app.dependency_overrides[symptom_routes.get_current_user_from_header] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db

    history_payload = [{"id": session_id, "analysis_status": "completed"}]
    detail_payload = {
        "id": session_id,
        "analysis_status": "completed",
        "timeline": {"saved_to_timeline": True},
    }

    with patch.object(symptom_routes.SymptomAnalysisService, "get_history", return_value=history_payload) as history_mock, patch.object(
        symptom_routes.SymptomAnalysisService,
        "get_one",
        return_value=detail_payload,
    ) as get_one_mock, patch.object(
        symptom_routes.SymptomAnalysisService,
        "save_to_timeline",
        return_value=detail_payload,
    ) as save_mock:
        client = TestClient(app)
        history_response = client.get("/api/v1/symptoms/history?limit=5")
        detail_response = client.get(f"/api/v1/symptoms/{session_id}")
        save_response = client.post(f"/api/v1/symptoms/{session_id}/timeline", json={"force": False})

    assert history_response.status_code == 200
    assert history_response.json()["data"] == history_payload
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id"] == session_id
    assert save_response.status_code == 200
    assert save_response.json()["data"]["timeline"]["saved_to_timeline"] is True
    history_mock.assert_called_once_with(db, current_user, limit=5)
    get_one_mock.assert_called_once_with(db, current_user, session_id)
    save_mock.assert_called_once_with(db, current_user, session_id, force=False)
