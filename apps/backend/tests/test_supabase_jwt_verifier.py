from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt import algorithms

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from core.config import settings
from services.supabase_jwt_verifier import SupabaseJWTVerifier


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    def __init__(self, payload: dict | None = None, error: Exception | None = None):
        self.payload = payload
        self.error = error
        self.calls = 0

    async def get(self, *_args, **_kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return FakeResponse(self.payload or {"keys": []})

    async def aclose(self) -> None:
        return None


def _configure_supabase_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_JWT_ISSUER", "https://example.supabase.co/auth/v1")
    monkeypatch.setattr(settings, "SUPABASE_AUDIENCE", "authenticated")
    monkeypatch.setattr(settings, "SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setattr(settings, "SUPABASE_JWKS_CACHE_TTL_SECONDS", 600)
    monkeypatch.setattr(settings, "SUPABASE_JWKS_STALE_TTL_SECONDS", 3600)
    monkeypatch.setattr(settings, "SUPABASE_JWKS_FETCH_TIMEOUT_SECONDS", 1.0)
    monkeypatch.setattr(settings, "SUPABASE_JWKS_FETCH_RETRIES", 1)
    monkeypatch.setattr(settings, "SUPABASE_JWKS_RETRY_BACKOFF_SECONDS", 0.0)


def _build_signed_token():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    kid = "test-kid"
    jwk_payload = json.loads(algorithms.RSAAlgorithm.to_jwk(public_key))
    jwk_payload["kid"] = kid
    token = jwt.encode(
        {
            "sub": "11111111-1111-1111-1111-111111111111",
            "email": "patient@example.com",
            "aud": "authenticated",
            "iss": "https://example.supabase.co/auth/v1",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )
    return token, {"keys": [jwk_payload]}


def test_decode_token_uses_cached_jwks_between_requests(monkeypatch: pytest.MonkeyPatch):
    _configure_supabase_settings(monkeypatch)
    token, jwks_payload = _build_signed_token()
    verifier = SupabaseJWTVerifier()
    fake_client = FakeAsyncClient(payload=jwks_payload)
    verifier._client = fake_client

    first_claims = asyncio.run(verifier.decode_token(token))
    second_claims = asyncio.run(verifier.decode_token(token))

    assert first_claims["sub"] == second_claims["sub"] == "11111111-1111-1111-1111-111111111111"
    assert fake_client.calls == 1
    assert verifier.snapshot()["cache_hits"] >= 1


def test_refresh_falls_back_to_stale_jwks_cache(monkeypatch: pytest.MonkeyPatch):
    _configure_supabase_settings(monkeypatch)
    token, jwks_payload = _build_signed_token()
    verifier = SupabaseJWTVerifier()
    verifier._client = FakeAsyncClient(payload=jwks_payload)

    asyncio.run(verifier.decode_token(token))
    verifier._cache.expires_at_monotonic = time.monotonic() - 1
    verifier._cache.stale_deadline_monotonic = time.monotonic() + 60
    verifier._client = FakeAsyncClient(error=httpx.ConnectTimeout("timed out"))

    cache = asyncio.run(verifier._refresh(reason="stale_test", allow_stale=True, force=True))

    assert cache.has_keys is True
    assert verifier.snapshot()["stale_fallback_uses"] == 1
    assert verifier.snapshot()["jwks_fetch_failures"] >= 1


def test_decode_token_returns_service_unavailable_when_no_jwks_cache_exists(monkeypatch: pytest.MonkeyPatch):
    _configure_supabase_settings(monkeypatch)
    token, _jwks_payload = _build_signed_token()
    verifier = SupabaseJWTVerifier()
    verifier._client = FakeAsyncClient(error=httpx.ConnectTimeout("timed out"))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verifier.decode_token(token))

    assert exc_info.value.status_code == 503
