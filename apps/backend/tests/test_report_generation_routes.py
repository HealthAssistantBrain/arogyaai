from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
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
from routes import report_generation as report_generation_routes


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(report_generation_routes.router)
    return app


def test_report_generation_routes_return_service_payloads():
    app = _build_app()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4())
    generated_id = str(uuid4())
    app.dependency_overrides[report_generation_routes.get_current_user_from_header] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db

    payload = {
        "id": generated_id,
        "title": "AI Longitudinal Clinical Report",
        "timeline": {"saved_to_timeline": True},
        "export": {"pdf_endpoint": f"/api/v1/report-generation/{generated_id}/export"},
    }

    with patch.object(report_generation_routes.ReportGenerationService, "generate", return_value=payload) as generate_mock, patch.object(
        report_generation_routes.ReportGenerationService,
        "history",
        return_value=[payload],
    ) as history_mock, patch.object(
        report_generation_routes.ReportGenerationService,
        "get_one",
        return_value=payload,
    ) as get_one_mock:
        client = TestClient(app)
        generate_response = client.post(
            "/api/v1/report-generation/generate",
            json={
                "title": "AI Longitudinal Clinical Report",
                "report_ids": [],
                "symptom_session_ids": [],
                "include_wearables": True,
                "include_biomarkers": True,
                "include_timeline_events": True,
            },
        )
        history_response = client.get("/api/v1/report-generation/history?limit=5")
        detail_response = client.get(f"/api/v1/report-generation/{generated_id}")

    assert generate_response.status_code == 200
    assert generate_response.json()["data"]["id"] == generated_id
    assert history_response.status_code == 200
    assert history_response.json()["data"][0]["id"] == generated_id
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["title"] == "AI Longitudinal Clinical Report"
    generate_mock.assert_called_once()
    history_mock.assert_called_once_with(db, current_user, limit=5)
    get_one_mock.assert_called_once_with(db, current_user, generated_id)
