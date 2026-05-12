from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any, Awaitable, Callable

logger = logging.getLogger("uvicorn.error")


def _clone(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


class WorkflowCache:
    def __init__(self, *, default_ttl_seconds: float | None = None) -> None:
        configured_ttl = default_ttl_seconds
        if configured_ttl is None:
            try:
                configured_ttl = float(os.getenv("AI_WORKFLOW_CACHE_TTL_SECONDS", "600"))
            except (TypeError, ValueError):
                configured_ttl = 600.0
        self.default_ttl_seconds = max(30.0, float(configured_ttl))
        self._items: dict[str, tuple[float, Any]] = {}
        self._items_lock = threading.Lock()
        self._inflight: dict[str, asyncio.Task] = {}
        self._inflight_lock = asyncio.Lock()

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._items_lock:
            cached = self._items.get(key)
            if cached is None:
                return None
            expires_at, payload = cached
            if now >= expires_at:
                self._items.pop(key, None)
                return None
            return _clone(payload)

    def set(self, key: str, payload: Any, *, ttl_seconds: float | None = None) -> Any:
        resolved_ttl = max(1.0, float(ttl_seconds or self.default_ttl_seconds))
        cached_payload = _clone(payload)
        with self._items_lock:
            self._items[key] = (time.monotonic() + resolved_ttl, cached_payload)
        return _clone(cached_payload)

    def delete(self, key: str) -> None:
        with self._items_lock:
            self._items.pop(key, None)

    async def run_singleflight(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        *,
        ttl_seconds: float | None = None,
        use_cache: bool = True,
        workflow: str = "generic",
        resource: str = "",
    ) -> Any:
        if use_cache:
            cached = self.get(key)
            if cached is not None:
                logger.info("[WORKFLOW_CACHE_HIT] workflow=%s resource=%s key=%s", workflow, resource or "-", key[:16])
                return cached

        owner = False
        async with self._inflight_lock:
            active_task = self._inflight.get(key)
            if active_task is None or active_task.done():
                logger.info("[WORKFLOW_CACHE_MISS] workflow=%s resource=%s key=%s", workflow, resource or "-", key[:16])
                active_task = asyncio.create_task(factory(), name=f"workflow-cache:{workflow}:{resource or key[:8]}")
                self._inflight[key] = active_task
                owner = True
            else:
                logger.info("[REQUEST_DEDUPED] workflow=%s resource=%s key=%s", workflow, resource or "-", key[:16])

        try:
            payload = await active_task
            if owner:
                self.set(key, payload, ttl_seconds=ttl_seconds)
            return _clone(payload)
        finally:
            if owner:
                async with self._inflight_lock:
                    current_task = self._inflight.get(key)
                    if current_task is active_task:
                        self._inflight.pop(key, None)


_WORKFLOW_CACHE: WorkflowCache | None = None


def get_workflow_cache() -> WorkflowCache:
    global _WORKFLOW_CACHE
    if _WORKFLOW_CACHE is None:
        _WORKFLOW_CACHE = WorkflowCache()
    return _WORKFLOW_CACHE
