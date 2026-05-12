from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass

from .cooldown_manager import cooldown_seconds_for

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - optional dependency fallback
    Redis = None  # type: ignore[assignment]

logger = logging.getLogger("google_fit_availability_cache")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()


@dataclass
class MetricAvailabilityRecord:
    metric_name: str
    reason: str
    detail: str
    observed_at: float
    expires_at: float
    cooldown_seconds: int

    @property
    def expired(self) -> bool:
        return time.time() >= float(self.expires_at)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str | bytes | None) -> "MetricAvailabilityRecord | None":
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        try:
            return cls(
                metric_name=str(payload.get("metric_name") or ""),
                reason=str(payload.get("reason") or ""),
                detail=str(payload.get("detail") or ""),
                observed_at=float(payload.get("observed_at") or 0.0),
                expires_at=float(payload.get("expires_at") or 0.0),
                cooldown_seconds=int(payload.get("cooldown_seconds") or 0),
            )
        except (TypeError, ValueError):
            return None


class GoogleFitAvailabilityCache:
    _memory_cache: dict[str, MetricAvailabilityRecord] = {}
    _memory_lock = asyncio.Lock()
    _redis_client: Redis | None | bool = None

    @classmethod
    def _key(cls, user_id: str, metric_name: str) -> str:
        return f"gfit:availability:{user_id}:{metric_name}"

    @classmethod
    async def get(cls, user_id: str, metric_name: str) -> MetricAvailabilityRecord | None:
        key = cls._key(user_id, metric_name)
        async with cls._memory_lock:
            cached = cls._memory_cache.get(key)
            if cached is not None:
                if cached.expired:
                    cls._memory_cache.pop(key, None)
                else:
                    return cached

        client = await cls._redis()
        if client is None:
            return None
        try:
            raw = await client.get(key)
        except Exception:
            return None
        record = MetricAvailabilityRecord.from_json(raw)
        if record is None or record.expired:
            return None
        async with cls._memory_lock:
            cls._memory_cache[key] = record
        return record

    @classmethod
    async def set(
        cls,
        user_id: str,
        metric_name: str,
        *,
        reason: str,
        detail: str = "",
        cooldown_seconds: int | None = None,
    ) -> MetricAvailabilityRecord:
        resolved_cooldown = int(cooldown_seconds or cooldown_seconds_for(reason))
        record = MetricAvailabilityRecord(
            metric_name=metric_name,
            reason=reason,
            detail=detail,
            observed_at=time.time(),
            expires_at=time.time() + resolved_cooldown,
            cooldown_seconds=resolved_cooldown,
        )
        key = cls._key(user_id, metric_name)
        async with cls._memory_lock:
            cls._memory_cache[key] = record

        client = await cls._redis()
        if client is not None:
            try:
                await client.set(key, record.to_json(), ex=resolved_cooldown)
            except Exception:
                logger.debug("[GFIT CACHE WRITE FAILED] key=%s", key, exc_info=True)

        return record

    @classmethod
    async def clear(cls, user_id: str, metric_name: str) -> None:
        key = cls._key(user_id, metric_name)
        async with cls._memory_lock:
            cls._memory_cache.pop(key, None)
        client = await cls._redis()
        if client is not None:
            try:
                await client.delete(key)
            except Exception:
                logger.debug("[GFIT CACHE CLEAR FAILED] key=%s", key, exc_info=True)

    @classmethod
    async def should_skip(cls, user_id: str, metric_name: str) -> MetricAvailabilityRecord | None:
        record = await cls.get(user_id, metric_name)
        if record is not None:
            logger.info(
                "[GFIT METRIC SKIPPED] user=%s metric=%s reason=%s cooldown_seconds=%s",
                user_id,
                metric_name,
                record.reason,
                record.cooldown_seconds,
            )
        return record

    @classmethod
    async def _redis(cls) -> Redis | None:
        if cls._redis_client is False:
            return None
        if cls._redis_client is not None:
            return cls._redis_client if isinstance(cls._redis_client, Redis) else None
        if Redis is None or not REDIS_URL:
            cls._redis_client = False
            return None
        try:
            cls._redis_client = Redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        except Exception:
            cls._redis_client = False
            return None
        return cls._redis_client if isinstance(cls._redis_client, Redis) else None
