from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, status
from jwt import algorithms

from core.config import settings

logger = logging.getLogger("supabase_jwt_verifier")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JWKSCacheState:
    payload: dict[str, Any] = field(default_factory=lambda: {"keys": []})
    keys_by_kid: dict[str, dict[str, Any]] = field(default_factory=dict)
    fetched_at: datetime | None = None
    fetched_at_monotonic: float | None = None
    expires_at_monotonic: float | None = None
    stale_deadline_monotonic: float | None = None
    last_error: str | None = None
    last_fetch_duration_ms: float | None = None

    @property
    def has_keys(self) -> bool:
        return bool(self.keys_by_kid)


class SupabaseJWTVerifier:
    def __init__(self) -> None:
        self._cache = JWKSCacheState()
        self._lock = asyncio.Lock()
        self._refresh_task: asyncio.Task[JWKSCacheState] | None = None
        self._client: httpx.AsyncClient | None = None
        self._metrics: dict[str, Any] = {
            "cache_hits": 0,
            "cache_misses": 0,
            "stale_hits": 0,
            "stale_fallback_uses": 0,
            "jwks_fetch_successes": 0,
            "jwks_fetch_failures": 0,
            "jwks_fetch_timeouts": 0,
            "verification_attempts": 0,
            "verification_successes": 0,
            "verification_failures": 0,
            "verification_retries": 0,
            "last_fetch_started_at": None,
            "last_fetch_completed_at": None,
            "last_fetch_reason": None,
            "last_fetch_error": None,
            "last_fetch_duration_ms": None,
            "last_verification_duration_ms": None,
            "startup_warmup_duration_ms": None,
            "startup_warmup_status": "idle",
        }

    @property
    def issuer(self) -> str:
        supabase_url = (settings.SUPABASE_URL or "").rstrip("/")
        return settings.SUPABASE_JWT_ISSUER or f"{supabase_url}/auth/v1"

    @property
    def audience(self) -> str:
        return settings.SUPABASE_AUDIENCE or ""

    @property
    def jwks_url(self) -> str:
        return f"{(settings.SUPABASE_URL or '').rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def cache_ttl_seconds(self) -> int:
        return max(30, int(settings.SUPABASE_JWKS_CACHE_TTL_SECONDS or 600))

    @property
    def stale_ttl_seconds(self) -> int:
        return max(self.cache_ttl_seconds, int(settings.SUPABASE_JWKS_STALE_TTL_SECONDS or 86400))

    @property
    def fetch_retries(self) -> int:
        return max(1, int(settings.SUPABASE_JWKS_FETCH_RETRIES or 2))

    @property
    def retry_backoff_seconds(self) -> float:
        return max(0.0, float(settings.SUPABASE_JWKS_RETRY_BACKOFF_SECONDS or 0.75))

    def _build_timeout(self) -> httpx.Timeout:
        timeout_seconds = max(0.5, float(settings.SUPABASE_JWKS_FETCH_TIMEOUT_SECONDS or 3.0))
        connect_timeout = min(timeout_seconds, max(0.25, timeout_seconds / 2))
        return httpx.Timeout(timeout_seconds, connect=connect_timeout)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._build_timeout(),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if settings.SUPABASE_ANON_KEY:
            headers["apikey"] = settings.SUPABASE_ANON_KEY
        return headers

    def _cache_age_seconds(self, cache: JWKSCacheState | None = None) -> float | None:
        state = cache or self._cache
        if state.fetched_at_monotonic is None:
            return None
        return max(0.0, round(time.monotonic() - state.fetched_at_monotonic, 3))

    def _is_fresh(self, cache: JWKSCacheState | None = None) -> bool:
        state = cache or self._cache
        return bool(
            state.has_keys
            and state.expires_at_monotonic is not None
            and time.monotonic() < state.expires_at_monotonic
        )

    def _is_stale_usable(self, cache: JWKSCacheState | None = None) -> bool:
        state = cache or self._cache
        return bool(
            state.has_keys
            and state.stale_deadline_monotonic is not None
            and time.monotonic() < state.stale_deadline_monotonic
        )

    def _public_key_from_jwk(self, jwk_payload: dict[str, Any], algorithm: str):
        if algorithm.startswith("RS"):
            return algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk_payload))
        if algorithm.startswith("ES"):
            return algorithms.ECAlgorithm.from_jwk(json.dumps(jwk_payload))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unsupported Supabase signing algorithm: {algorithm}",
        )

    def snapshot(self) -> dict[str, Any]:
        cache_age_seconds = self._cache_age_seconds()
        cache_state = "empty"
        if self._is_fresh():
            cache_state = "fresh"
        elif self._is_stale_usable():
            cache_state = "stale"

        if cache_state == "fresh":
            status_value = "ok"
        elif cache_state == "stale":
            status_value = "degraded"
        else:
            status_value = "degraded" if self._metrics["last_fetch_error"] else "warming"

        return {
            "status": status_value,
            "cache_state": cache_state,
            "cache_age_seconds": cache_age_seconds,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "stale_ttl_seconds": self.stale_ttl_seconds,
            "keys_cached": len(self._cache.keys_by_kid),
            "last_fetch_reason": self._metrics["last_fetch_reason"],
            "last_fetch_started_at": self._metrics["last_fetch_started_at"],
            "last_fetch_completed_at": self._metrics["last_fetch_completed_at"],
            "last_fetch_duration_ms": self._metrics["last_fetch_duration_ms"],
            "last_fetch_error": self._metrics["last_fetch_error"],
            "verification_attempts": self._metrics["verification_attempts"],
            "verification_successes": self._metrics["verification_successes"],
            "verification_failures": self._metrics["verification_failures"],
            "verification_retries": self._metrics["verification_retries"],
            "last_verification_duration_ms": self._metrics["last_verification_duration_ms"],
            "cache_hits": self._metrics["cache_hits"],
            "cache_misses": self._metrics["cache_misses"],
            "stale_hits": self._metrics["stale_hits"],
            "stale_fallback_uses": self._metrics["stale_fallback_uses"],
            "jwks_fetch_successes": self._metrics["jwks_fetch_successes"],
            "jwks_fetch_failures": self._metrics["jwks_fetch_failures"],
            "jwks_fetch_timeouts": self._metrics["jwks_fetch_timeouts"],
            "startup_warmup_status": self._metrics["startup_warmup_status"],
            "startup_warmup_duration_ms": self._metrics["startup_warmup_duration_ms"],
        }

    async def warm_cache(self, reason: str = "startup") -> dict[str, Any]:
        started_at = time.perf_counter()
        self._metrics["startup_warmup_status"] = "running"
        try:
            await self._refresh(reason=reason, allow_stale=True)
            self._metrics["startup_warmup_status"] = "ready"
        except Exception as exc:
            self._metrics["startup_warmup_status"] = "degraded"
            logger.warning("[Auth] JWKS startup warmup degraded | reason=%s error=%s", reason, exc)
        finally:
            self._metrics["startup_warmup_duration_ms"] = round((time.perf_counter() - started_at) * 1000, 2)
        return self.snapshot()

    async def decode_token(self, token: str) -> dict[str, Any]:
        if not settings.SUPABASE_URL:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase OAuth is not configured (SUPABASE_URL missing)",
            )

        started_at = time.perf_counter()
        self._metrics["verification_attempts"] += 1

        try:
            unverified_header = jwt.get_unverified_header(token)
            algorithm = str(unverified_header.get("alg") or "RS256")
            kid = str(unverified_header.get("kid") or "").strip()
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Supabase OAuth token is missing a signing key id",
                )

            claims = await self._decode_with_cached_key(
                token,
                algorithm=algorithm,
                kid=kid,
                force_refresh=False,
            )
            self._metrics["verification_successes"] += 1
            return claims
        except jwt.InvalidSignatureError:
            self._metrics["verification_retries"] += 1
            try:
                claims = await self._decode_with_cached_key(
                    token,
                    algorithm=algorithm,
                    kid=kid,
                    force_refresh=True,
                )
                self._metrics["verification_successes"] += 1
                return claims
            except HTTPException:
                self._metrics["verification_failures"] += 1
                raise
            except jwt.PyJWTError as exc:
                self._metrics["verification_failures"] += 1
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid Supabase OAuth token: {exc}",
                ) from exc
        except HTTPException:
            self._metrics["verification_failures"] += 1
            raise
        except jwt.PyJWTError as exc:
            self._metrics["verification_failures"] += 1
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Supabase OAuth token: {exc}",
            ) from exc
        except Exception as exc:
            self._metrics["verification_failures"] += 1
            logger.exception("[Auth] Unexpected Supabase token verification failure")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase token verification temporarily unavailable",
            ) from exc
        finally:
            self._metrics["last_verification_duration_ms"] = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "[Auth] Supabase token verification completed | duration_ms=%s cache_state=%s",
                self._metrics["last_verification_duration_ms"],
                self.snapshot().get("cache_state"),
            )

    async def _decode_with_cached_key(
        self,
        token: str,
        *,
        algorithm: str,
        kid: str,
        force_refresh: bool,
    ) -> dict[str, Any]:
        jwk_payload = await self._get_signing_jwk(kid, force_refresh=force_refresh)
        public_key = self._public_key_from_jwk(jwk_payload, algorithm)
        return jwt.decode(
            token,
            public_key,
            algorithms=[algorithm],
            audience=self.audience,
            issuer=self.issuer,
        )

    async def _get_signing_jwk(self, kid: str, *, force_refresh: bool = False) -> dict[str, Any]:
        cache = await self._ensure_cache(required_kid=kid, force_refresh=force_refresh)
        jwk_payload = cache.keys_by_kid.get(kid)
        if jwk_payload:
            return jwk_payload

        cache = await self._refresh(reason=f"kid_miss:{kid}", allow_stale=self._is_stale_usable(), force=True)
        jwk_payload = cache.keys_by_kid.get(kid)
        if jwk_payload:
            return jwk_payload

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supabase signing key not found",
        )

    async def _ensure_cache(self, *, required_kid: str, force_refresh: bool = False) -> JWKSCacheState:
        cache = self._cache
        if not force_refresh and self._is_fresh(cache):
            self._metrics["cache_hits"] += 1
            if required_kid in cache.keys_by_kid:
                logger.debug("[Auth] JWKS cache hit | kid=%s age_s=%s", required_kid, self._cache_age_seconds(cache))
                return cache

        if not force_refresh and self._is_stale_usable(cache) and required_kid in cache.keys_by_kid:
            self._metrics["stale_hits"] += 1
            self._schedule_background_refresh(reason=f"stale_refresh:{required_kid}")
            logger.warning(
                "[Auth] Using stale JWKS cache | kid=%s age_s=%s",
                required_kid,
                self._cache_age_seconds(cache),
            )
            return cache

        self._metrics["cache_misses"] += 1
        return await self._refresh(
            reason=f"cache_miss:{required_kid}",
            allow_stale=self._is_stale_usable(cache),
            force=force_refresh,
        )

    def _schedule_background_refresh(self, *, reason: str) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        if self._refresh_task and not self._refresh_task.done():
            return

        task = loop.create_task(self._refresh(reason=reason, allow_stale=True, force=True))
        self._refresh_task = task

        def _cleanup(done_task: asyncio.Task[Any]) -> None:
            if done_task.cancelled():
                return
            if done_task.exception():
                logger.warning("[Auth] Background JWKS refresh failed | reason=%s error=%s", reason, done_task.exception())

        task.add_done_callback(_cleanup)

    async def _refresh(
        self,
        *,
        reason: str,
        allow_stale: bool,
        force: bool = False,
    ) -> JWKSCacheState:
        cache = self._cache
        if not force and self._is_fresh(cache):
            return cache

        async with self._lock:
            if not force and self._is_fresh(self._cache):
                return self._cache

            if self._refresh_task and not self._refresh_task.done():
                task = self._refresh_task
            else:
                task = asyncio.create_task(self._fetch_and_store(reason=reason))
                self._refresh_task = task

        try:
            return await task
        except Exception as exc:
            if allow_stale and self._is_stale_usable(self._cache):
                self._metrics["stale_fallback_uses"] += 1
                logger.warning(
                    "[Auth] JWKS refresh failed; falling back to stale cache | reason=%s error=%s age_s=%s",
                    reason,
                    exc,
                    self._cache_age_seconds(),
                )
                return self._cache

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase JWKS temporarily unavailable",
            ) from exc
        finally:
            async with self._lock:
                if self._refresh_task is task and task.done():
                    self._refresh_task = None

    async def _fetch_and_store(self, *, reason: str) -> JWKSCacheState:
        last_error: Exception | None = None
        self._metrics["last_fetch_reason"] = reason
        self._metrics["last_fetch_started_at"] = _utc_now().isoformat()

        for attempt in range(1, self.fetch_retries + 1):
            started_at = time.perf_counter()
            try:
                response = await self._get_client().get(
                    self.jwks_url,
                    headers=self._auth_headers(),
                )
                response.raise_for_status()
                payload = response.json()
                keys = payload.get("keys")
                if not isinstance(keys, list) or not keys:
                    raise ValueError("Supabase JWKS response did not include signing keys")

                now_monotonic = time.monotonic()
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
                cache = JWKSCacheState(
                    payload=payload,
                    keys_by_kid={str(key.get("kid")): key for key in keys if key.get("kid")},
                    fetched_at=_utc_now(),
                    fetched_at_monotonic=now_monotonic,
                    expires_at_monotonic=now_monotonic + self.cache_ttl_seconds,
                    stale_deadline_monotonic=now_monotonic + self.stale_ttl_seconds,
                    last_fetch_duration_ms=duration_ms,
                )
                self._cache = cache
                self._metrics["jwks_fetch_successes"] += 1
                self._metrics["last_fetch_completed_at"] = _utc_now().isoformat()
                self._metrics["last_fetch_duration_ms"] = duration_ms
                self._metrics["last_fetch_error"] = None
                logger.info(
                    "[Auth] JWKS refresh succeeded | reason=%s attempt=%s/%s duration_ms=%s keys=%s",
                    reason,
                    attempt,
                    self.fetch_retries,
                    duration_ms,
                    len(cache.keys_by_kid),
                )
                return cache
            except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
                last_error = exc
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
                self._metrics["jwks_fetch_failures"] += 1
                self._metrics["last_fetch_duration_ms"] = duration_ms
                self._metrics["last_fetch_completed_at"] = _utc_now().isoformat()
                self._metrics["last_fetch_error"] = str(exc)
                if isinstance(exc, httpx.TimeoutException):
                    self._metrics["jwks_fetch_timeouts"] += 1
                logger.warning(
                    "[Auth] JWKS refresh failed | reason=%s attempt=%s/%s duration_ms=%s error=%s",
                    reason,
                    attempt,
                    self.fetch_retries,
                    duration_ms,
                    exc,
                )
                if attempt < self.fetch_retries and self.retry_backoff_seconds:
                    await asyncio.sleep(self.retry_backoff_seconds * (2 ** (attempt - 1)))

        if last_error is not None:
            raise last_error

        raise RuntimeError("Supabase JWKS refresh failed without an explicit error")

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


supabase_jwt_verifier = SupabaseJWTVerifier()


def get_supabase_auth_snapshot() -> dict[str, Any]:
    return supabase_jwt_verifier.snapshot()
