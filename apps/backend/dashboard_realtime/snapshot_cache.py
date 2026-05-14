from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from copy import deepcopy
from typing import Any

from core.redis_resilience import get_resilient_redis_pool

logger = logging.getLogger("dashboard_snapshot_cache")

SNAPSHOT_TTL_SECONDS = max(15, int(os.getenv("DASHBOARD_SNAPSHOT_TTL_SECONDS", "90")))
SNAPSHOT_STALE_TTL_SECONDS = max(SNAPSHOT_TTL_SECONDS, int(os.getenv("DASHBOARD_SNAPSHOT_STALE_TTL_SECONDS", "900")))
REDIS_OPERATION_TIMEOUT_SECONDS = max(0.1, float(os.getenv("DASHBOARD_SNAPSHOT_REDIS_TIMEOUT_SECONDS", "0.35")))
REDIS_POOL_NAME = "dashboard-realtime"


class RealtimeSnapshotCache:
    _memory_cache: dict[str, tuple[float, dict[str, Any]]] = {}
    _last_valid_cache: dict[str, dict[str, Any]] = {}
    _lock = asyncio.Lock()

    @classmethod
    def key(cls, kind: str, user_id: str) -> str:
        return f"dashboard:snapshot:{kind}:{user_id}"

    @classmethod
    def stale_key(cls, key: str) -> str:
        return f"{key}:last_valid"

    @classmethod
    async def get(cls, kind: str, user_id: str) -> dict[str, Any] | None:
        key = cls.key(kind, user_id)
        now = time.monotonic()
        async with cls._lock:
            cached = cls._memory_cache.get(key)
            if cached is not None:
                expires_at, payload = cached
                if now < expires_at:
                    logger.info("[REALTIME CACHE HIT] kind=%s user_id=%s source=memory", kind, user_id)
                    return deepcopy(payload)
                cls._last_valid_cache[key] = deepcopy(payload)
                cls._memory_cache.pop(key, None)

        raw = await cls._redis_get(key)
        if raw is None:
            logger.info("[REALTIME CACHE MISS] kind=%s user_id=%s", kind, user_id)
            return None

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("[REALTIME CACHE MISS] kind=%s user_id=%s reason=invalid_json", kind, user_id)
            return None

        async with cls._lock:
            cls._memory_cache[key] = (time.monotonic() + float(SNAPSHOT_TTL_SECONDS), deepcopy(payload))
            cls._last_valid_cache[key] = deepcopy(payload)

        logger.info("[REALTIME CACHE HIT] kind=%s user_id=%s source=redis", kind, user_id)
        return deepcopy(payload)

    @classmethod
    async def get_stale(cls, kind: str, user_id: str) -> dict[str, Any] | None:
        key = cls.key(kind, user_id)
        async with cls._lock:
            cached = cls._last_valid_cache.get(key)
            if cached is not None:
                return deepcopy(cached)
            cached_with_expiry = cls._memory_cache.get(key)
            if cached_with_expiry is not None:
                return deepcopy(cached_with_expiry[1])

        raw = await cls._redis_get(cls.stale_key(key))
        if raw is None:
            return None
        try:
            return deepcopy(json.loads(raw))
        except json.JSONDecodeError:
            return None

    @classmethod
    async def set(cls, kind: str, user_id: str, payload: dict[str, Any], *, ttl_seconds: int = SNAPSHOT_TTL_SECONDS) -> None:
        key = cls.key(kind, user_id)
        cached_payload = deepcopy(payload)
        async with cls._lock:
            cls._memory_cache[key] = (time.monotonic() + float(ttl_seconds), deepcopy(cached_payload))
            cls._last_valid_cache[key] = deepcopy(cached_payload)

        await cls._redis_set(key, cached_payload, ttl_seconds=ttl_seconds)
        await cls._redis_set(cls.stale_key(key), cached_payload, ttl_seconds=SNAPSHOT_STALE_TTL_SECONDS)

    @classmethod
    async def _redis_get(cls, key: str) -> str | None:
        pool = await get_resilient_redis_pool(REDIS_POOL_NAME)
        try:
            return await asyncio.wait_for(
                pool.call("get", lambda client: client.get(key)),
                timeout=REDIS_OPERATION_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.debug("[REALTIME CACHE REDIS GET FAILED] key=%s", key, exc_info=True)
            return None

    @classmethod
    async def _redis_set(cls, key: str, payload: dict[str, Any], *, ttl_seconds: int) -> None:
        pool = await get_resilient_redis_pool(REDIS_POOL_NAME)
        try:
            await asyncio.wait_for(
                pool.call(
                    "set",
                    lambda client: client.set(key, json.dumps(payload, default=str), ex=int(ttl_seconds)),
                ),
                timeout=REDIS_OPERATION_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.debug("[REALTIME CACHE REDIS SET FAILED] key=%s", key, exc_info=True)
