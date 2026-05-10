from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

from sqlalchemy.orm import Session

from database.session import SessionLocal
from models import User
from services.prediction_explanation_service import PredictionExplanationService

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - optional dependency fallback
    Redis = None  # type: ignore[assignment]

logger = logging.getLogger("uvicorn.error")

PROGRESSIVE_AI_CACHE_TTL_SECONDS = max(15.0, float(os.getenv("PROGRESSIVE_AI_CACHE_TTL_SECONDS", "300")))
PROGRESSIVE_AI_POLL_AFTER_MS = max(250, int(os.getenv("PROGRESSIVE_AI_POLL_AFTER_MS", "900")))
PROGRESSIVE_AI_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()


def _clone_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    return json.loads(json.dumps(payload or {}, default=str))


class ProgressiveAIService:
    _memory_cache: dict[str, tuple[float, dict[str, Any]]] = {}
    _inflight_tasks: dict[str, asyncio.Task] = {}
    _lock = asyncio.Lock()
    _redis_client: Redis | None | bool = None

    @classmethod
    async def get_prediction_explanation(
        cls,
        db: Session,
        user: User,
        *,
        prediction_id: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        resource_key = cls._prediction_explanation_resource_key(user_id=str(user.id), prediction_id=prediction_id)

        if not force_refresh:
            cached = await cls._cache_get(resource_key)
            if cls._is_ready_payload(cached):
                return cls._with_meta(cached, resource_key=resource_key, inflight=cls._is_inflight(resource_key))

        snapshot = await PredictionExplanationService.get_prediction_explanation(
            db,
            user,
            prediction_id=prediction_id,
            force_refresh=False,
            allow_generation=False,
        )
        if cls._is_ready_payload(snapshot) and not force_refresh:
            await cls._cache_set(resource_key, snapshot)
            return cls._with_meta(snapshot, resource_key=resource_key, inflight=False)

        await cls._ensure_prediction_explanation_refresh(
            user_id=str(user.id),
            prediction_id=prediction_id,
            resource_key=resource_key,
        )

        return cls._with_meta(
            {
                **_clone_payload(snapshot),
                "status": "processing",
                "source": "background_refresh",
            },
            resource_key=resource_key,
            inflight=True,
            stale=bool(snapshot.get("data")),
        )

    @classmethod
    async def _ensure_prediction_explanation_refresh(
        cls,
        *,
        user_id: str,
        prediction_id: str | None,
        resource_key: str,
    ) -> None:
        async with cls._lock:
            active_task = cls._inflight_tasks.get(resource_key)
            if active_task is not None and not active_task.done():
                return

            task = asyncio.create_task(
                cls._refresh_prediction_explanation(
                    user_id=user_id,
                    prediction_id=prediction_id,
                    resource_key=resource_key,
                ),
                name=f"progressive-ai:{resource_key}",
            )
            cls._inflight_tasks[resource_key] = task

            def _cleanup(done_task: asyncio.Task, *, key: str = resource_key) -> None:
                current = cls._inflight_tasks.get(key)
                if current is done_task:
                    cls._inflight_tasks.pop(key, None)
                try:
                    done_task.result()
                except Exception as exc:  # pragma: no cover - background observation
                    logger.warning("Progressive AI refresh failed | key=%s error=%s", key, exc)

            task.add_done_callback(_cleanup)

    @classmethod
    async def _refresh_prediction_explanation(
        cls,
        *,
        user_id: str,
        prediction_id: str | None,
        resource_key: str,
    ) -> dict[str, Any]:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
            if user is None:
                raise RuntimeError(f"User {user_id} was not found for progressive explanation refresh")
            payload = await PredictionExplanationService.get_prediction_explanation(
                db,
                user,
                prediction_id=prediction_id,
                force_refresh=True,
                allow_generation=True,
            )
            await cls._cache_set(resource_key, payload)
            return payload
        finally:
            db.close()

    @classmethod
    async def _cache_get(cls, key: str) -> dict[str, Any] | None:
        now = time.monotonic()
        cached = cls._memory_cache.get(key)
        if cached is not None:
            expires_at, payload = cached
            if now < expires_at:
                return _clone_payload(payload)
            cls._memory_cache.pop(key, None)

        client = await cls._redis()
        if client is None:
            return None
        try:
            raw = await client.get(key)
        except Exception as exc:
            logger.debug("Progressive AI redis read failed | key=%s error=%s", key, exc)
            return None
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        cls._memory_cache[key] = (now + PROGRESSIVE_AI_CACHE_TTL_SECONDS, payload)
        return _clone_payload(payload)

    @classmethod
    async def _cache_set(cls, key: str, payload: dict[str, Any]) -> None:
        cached_payload = _clone_payload(payload)
        cls._memory_cache[key] = (time.monotonic() + PROGRESSIVE_AI_CACHE_TTL_SECONDS, cached_payload)
        client = await cls._redis()
        if client is None:
            return
        try:
            await client.set(key, json.dumps(cached_payload, default=str), ex=int(PROGRESSIVE_AI_CACHE_TTL_SECONDS))
        except Exception as exc:
            logger.debug("Progressive AI redis write failed | key=%s error=%s", key, exc)

    @classmethod
    async def _redis(cls) -> Redis | None:
        if cls._redis_client is False:
            return None
        if cls._redis_client is not None:
            return cls._redis_client if isinstance(cls._redis_client, Redis) else None
        if Redis is None or not PROGRESSIVE_AI_REDIS_URL:
            cls._redis_client = False
            return None
        try:
            cls._redis_client = Redis.from_url(PROGRESSIVE_AI_REDIS_URL, encoding="utf-8", decode_responses=True)
        except Exception:
            cls._redis_client = False
            return None
        return cls._redis_client if isinstance(cls._redis_client, Redis) else None

    @classmethod
    def _prediction_explanation_resource_key(cls, *, user_id: str, prediction_id: str | None) -> str:
        return f"progressive:prediction_explanation:{user_id}:{prediction_id or 'latest'}"

    @classmethod
    def _is_ready_payload(cls, payload: dict[str, Any] | None) -> bool:
        return bool(payload) and str(payload.get("status") or "").lower() == "ready" and isinstance(payload.get("data"), dict)

    @classmethod
    def _is_inflight(cls, resource_key: str) -> bool:
        task = cls._inflight_tasks.get(resource_key)
        return task is not None and not task.done()

    @classmethod
    def _with_meta(
        cls,
        payload: dict[str, Any],
        *,
        resource_key: str,
        inflight: bool,
        stale: bool = False,
    ) -> dict[str, Any]:
        response = _clone_payload(payload)
        meta = response.get("meta") if isinstance(response.get("meta"), dict) else {}
        meta.update(
            {
                "resource_key": resource_key,
                "inflight": inflight,
                "stale": stale,
                "poll_after_ms": PROGRESSIVE_AI_POLL_AFTER_MS if inflight else 0,
            }
        )
        response["meta"] = meta
        return response
