from __future__ import annotations

from typing import Any, Awaitable, Callable

from ai.cache import get_workflow_cache


class ProviderMemory:
    TTL_SECONDS = 300.0

    def __init__(self) -> None:
        self.cache = get_workflow_cache()

    async def remember(self, key: str, factory: Callable[[], Awaitable[Any]], *, ttl_seconds: float | None = None) -> Any:
        return await self.cache.run_singleflight(
            key,
            factory,
            ttl_seconds=ttl_seconds or self.TTL_SECONDS,
            workflow="provider_intelligence",
            resource=key.split(":")[-1],
        )

    def get(self, key: str) -> Any | None:
        return self.cache.get(key)

    def set(self, key: str, payload: Any, *, ttl_seconds: float | None = None) -> Any:
        return self.cache.set(key, payload, ttl_seconds=ttl_seconds or self.TTL_SECONDS)
