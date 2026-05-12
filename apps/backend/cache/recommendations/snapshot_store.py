from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - optional dependency fallback
    Redis = None  # type: ignore[assignment]

logger = logging.getLogger("recommendation_snapshot_store")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()
REDIS_TIMEOUT_SECONDS = max(0.1, float(os.getenv("RECOMMENDATION_CACHE_REDIS_TIMEOUT_SECONDS", "0.5")))
STALE_TTL_SECONDS = max(3600, int(os.getenv("RECOMMENDATION_SNAPSHOT_STALE_TTL_SECONDS", "86400")))
PERSIST_TO_DB = os.getenv("RECOMMENDATION_SNAPSHOT_DB_PERSIST_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


class RecommendationSnapshotStore:
    _memory_cache: dict[str, tuple[float, dict[str, Any]]] = {}
    _last_valid_cache: dict[str, dict[str, Any]] = {}
    _lock = asyncio.Lock()
    _redis_client: Redis | None | bool = None

    @classmethod
    async def get(cls, key: str) -> dict[str, Any] | None:
        now = time.monotonic()
        async with cls._lock:
            cached = cls._memory_cache.get(key)
            if cached is not None:
                expires_at, payload = cached
                if now < expires_at:
                    return deepcopy(payload)
                cls._last_valid_cache[key] = deepcopy(payload)
                cls._memory_cache.pop(key, None)

        client = await cls._redis()
        if client is None:
            return await cls._get_db(key, allow_expired=False)
        try:
            raw = await asyncio.wait_for(client.get(key), timeout=REDIS_TIMEOUT_SECONDS)
        except Exception:
            return await cls._get_db(key, allow_expired=False)
        if not raw:
            return await cls._get_db(key, allow_expired=False)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return await cls._get_db(key, allow_expired=False)
        return deepcopy(payload)

    @classmethod
    async def get_stale(cls, key: str) -> dict[str, Any] | None:
        async with cls._lock:
            cached = cls._last_valid_cache.get(key)
            if cached is not None:
                return deepcopy(cached)
            cached_with_expiry = cls._memory_cache.get(key)
            if cached_with_expiry is not None:
                return deepcopy(cached_with_expiry[1])

        client = await cls._redis()
        if client is not None:
            try:
                raw = await asyncio.wait_for(client.get(cls._stale_key(key)), timeout=REDIS_TIMEOUT_SECONDS)
            except Exception:
                raw = None
            if raw:
                try:
                    return deepcopy(json.loads(raw))
                except json.JSONDecodeError:
                    pass

        return await cls._get_db(key, allow_expired=True)

    @classmethod
    async def set(cls, key: str, payload: dict[str, Any], *, ttl_seconds: int) -> None:
        cached_payload = deepcopy(payload)
        async with cls._lock:
            cls._memory_cache[key] = (time.monotonic() + float(ttl_seconds), cached_payload)
            cls._last_valid_cache[key] = deepcopy(cached_payload)
        client = await cls._redis()
        if client is not None:
            try:
                await asyncio.wait_for(
                    client.set(key, json.dumps(cached_payload, default=str), ex=int(ttl_seconds)),
                    timeout=REDIS_TIMEOUT_SECONDS,
                )
                await asyncio.wait_for(
                    client.set(cls._stale_key(key), json.dumps(cached_payload, default=str), ex=STALE_TTL_SECONDS),
                    timeout=REDIS_TIMEOUT_SECONDS,
                )
            except Exception:
                logger.debug("[RECOMMENDATION CACHE WRITE FAILED] key=%s", key, exc_info=True)
        if PERSIST_TO_DB:
            await cls._set_db(key, cached_payload, ttl_seconds=ttl_seconds)

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
            cls._redis_client = Redis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
                socket_timeout=REDIS_TIMEOUT_SECONDS,
                health_check_interval=30,
            )
        except Exception:
            cls._redis_client = False
            return None
        return cls._redis_client if isinstance(cls._redis_client, Redis) else None

    @staticmethod
    def _stale_key(key: str) -> str:
        return f"{key}:last_valid"

    @staticmethod
    def _key_parts(key: str) -> tuple[UUID | None, str | None]:
        parts = key.split(":")
        if len(parts) < 4:
            return None, None
        try:
            user_id = UUID(parts[2])
        except (TypeError, ValueError):
            user_id = None
        prediction_id = parts[3] if parts[3] and parts[3] != "latest" else None
        return user_id, prediction_id

    @classmethod
    async def _set_db(cls, key: str, payload: dict[str, Any], *, ttl_seconds: int) -> None:
        try:
            await asyncio.to_thread(cls._set_db_sync, key, payload, ttl_seconds)
        except Exception:
            logger.debug("[RECOMMENDATION CACHE DB WRITE FAILED] key=%s", key, exc_info=True)

    @classmethod
    def _set_db_sync(cls, key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        from database.session import SessionLocal
        from models import RecommendationSnapshotRecord

        user_id, prediction_id = cls._key_parts(key)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(ttl_seconds))
        session = SessionLocal()
        try:
            row = session.query(RecommendationSnapshotRecord).filter(RecommendationSnapshotRecord.cache_key == key).first()
            if row is None:
                row = RecommendationSnapshotRecord(cache_key=key)
                session.add(row)
            row.user_id = user_id
            row.prediction_id = prediction_id
            row.status = str(payload.get("status") or "ready") if isinstance(payload, dict) else "ready"
            row.source = str(payload.get("source") or "snapshot_cache") if isinstance(payload, dict) else "snapshot_cache"
            row.payload = deepcopy(payload)
            row.expires_at = expires_at
            session.commit()
        finally:
            session.close()

    @classmethod
    async def _get_db(cls, key: str, *, allow_expired: bool = False) -> dict[str, Any] | None:
        if not PERSIST_TO_DB:
            return None
        try:
            return await asyncio.to_thread(cls._get_db_sync, key, allow_expired)
        except Exception:
            logger.debug("[RECOMMENDATION CACHE DB READ FAILED] key=%s", key, exc_info=True)
            return None

    @classmethod
    def _get_db_sync(cls, key: str, allow_expired: bool) -> dict[str, Any] | None:
        from sqlalchemy import or_

        from database.session import SessionLocal
        from models import RecommendationSnapshotRecord

        session = SessionLocal()
        try:
            query = session.query(RecommendationSnapshotRecord).filter(RecommendationSnapshotRecord.cache_key == key)
            if not allow_expired:
                query = query.filter(
                    or_(
                        RecommendationSnapshotRecord.expires_at.is_(None),
                        RecommendationSnapshotRecord.expires_at > datetime.now(timezone.utc),
                    )
                )
            row = query.order_by(RecommendationSnapshotRecord.updated_at.desc()).first()
            if row is None or not isinstance(row.payload, dict):
                return None
            return deepcopy(row.payload)
        finally:
            session.close()
