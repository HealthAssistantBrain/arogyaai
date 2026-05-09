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
from routes import auth as auth_routes
from routes import profile as profile_routes


def _build_auth_app() -> FastAPI:
    app = FastAPI()
    app.include_router(auth_routes.router)
    return app


def _build_profile_app() -> FastAPI:
    app = FastAPI()
    app.include_router(profile_routes.router)
    return app


def test_legacy_login_signup_and_refresh_routes_stay_supabase_owned():
    client = TestClient(_build_auth_app())

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "patient@example.com", "password": "StrongPass123!"},
    )
    signup_response = client.post(
        "/api/v1/auth/signup",
        json={"email": "patient@example.com", "password": "StrongPass123!", "full_name": "Patient Example"},
    )
    refresh_response = client.post("/api/v1/auth/refresh", json={})

    assert login_response.status_code == 410
    assert signup_response.status_code == 410
    assert refresh_response.status_code == 410
    assert "Supabase" in login_response.json()["detail"]
    assert "Supabase" in signup_response.json()["detail"]
    assert "Supabase" in refresh_response.json()["detail"]


def test_social_login_syncs_supabase_user_and_returns_user_contract():
    app = _build_auth_app()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4())
    claims = {
        "sub": str(uuid4()),
        "email": "patient@example.com",
        "auth_provider": "supabase",
    }
    app.dependency_overrides[auth_routes.get_supabase_claims_from_header] = lambda: claims
    app.dependency_overrides[get_db] = lambda: db

    with patch.object(auth_routes.AuthService, "get_or_create_user_from_supabase_claims", return_value=current_user) as create_mock, patch.object(
        auth_routes.UserService,
        "get_user_me",
        return_value={"success": True, "data": {"id": str(current_user.id)}},
    ):
        response = TestClient(app).post("/api/v1/auth/social-login")

    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"id": str(current_user.id)}}
    create_mock.assert_called_once_with(db, claims)


def test_verify_email_uses_authenticated_user_dependency():
    app = _build_auth_app()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4())
    app.dependency_overrides[auth_routes.get_current_user_from_header] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db

    with patch.object(
        auth_routes.AuthService,
        "verify_email",
        return_value={"success": True, "data": {"is_email_verified": True}},
    ) as verify_mock:
        response = TestClient(app).post("/api/v1/auth/verify-email")

    assert response.status_code == 200
    assert response.json()["data"]["is_email_verified"] is True
    verify_mock.assert_called_once_with(db, current_user.id)


def test_logout_returns_session_cleared_payload_without_bearer_token():
    response = TestClient(_build_auth_app()).post("/api/v1/auth/logout")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "status": "ready",
        "data": {"message": "Session cleared"},
    }


def test_profile_route_returns_profile_bundle_for_authenticated_user():
    app = _build_profile_app()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4())
    payload = {"success": True, "status": "ready", "data": {"user": {"id": str(current_user.id)}}}
    app.dependency_overrides[profile_routes.get_current_user_from_header] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db

    with patch.object(profile_routes.ProfileService, "get_profile_bundle", return_value=payload) as bundle_mock:
        response = TestClient(app).get("/api/v1/profile")

    assert response.status_code == 200
    assert response.json() == payload
    bundle_mock.assert_called_once_with(db, current_user)
