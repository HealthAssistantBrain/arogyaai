from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")
os.environ.setdefault("APP_ENCRYPTION_KEY", "dGVzdF9hcHBfZW5jcnlwdGlvbl9rZXlfMzJfYnl0ZXMhISE=")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test-chat-routes.db")
os.environ.setdefault("ANALYTICS_DB_MODE", "primary")

from database.session import get_db
from routes import chat as chat_routes


def _build_chat_app() -> FastAPI:
    app = FastAPI()
    app.include_router(chat_routes.router)
    return app


def test_chat_route_returns_json_payload_instead_of_http_500_on_runtime_failure():
    app = _build_chat_app()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4())
    app.dependency_overrides[chat_routes.get_current_user_from_header] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db

    with patch.object(chat_routes, "generate_chat_response", AsyncMock(side_effect=RuntimeError("chat boom"))):
        response = TestClient(app).post("/api/v1/chat", json={"query": "Hello", "history": []})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["status"] == "error"
    assert payload["error"]["detail"] == "chat boom"


def test_chat_route_rejects_blank_query_with_http_400():
    app = _build_chat_app()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4())
    app.dependency_overrides[chat_routes.get_current_user_from_header] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db

    response = TestClient(app).post("/api/v1/chat", json={"query": "   ", "history": []})

    assert response.status_code == 400
    assert "non-empty query" in response.json()["detail"].lower()


def test_chat_stream_route_terminates_with_error_and_final_events_on_runtime_failure():
    app = _build_chat_app()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4())
    app.dependency_overrides[chat_routes.get_current_user_from_header] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db

    async def _broken_stream(*args, **kwargs):
        if False:
            yield ""
        raise RuntimeError("stream boom")

    with patch.object(chat_routes, "stream_chat_response", _broken_stream):
        response = TestClient(app).post("/api/v1/chat/stream", json={"query": "Hello", "history": []})

    assert response.status_code == 200
    assert '"event": "error"' in response.text
    assert '"event": "final"' in response.text
    assert "stream boom" in response.text
