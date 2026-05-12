from __future__ import annotations

from typing import Any, Awaitable, Callable

from ai.cache import get_workflow_cache


class InterventionMemory:
    TTL_SECONDS = 420.0

    def __init__(self) -> None:
        self.cache = get_workflow_cache()

    async def remember(self, key: str, factory: Callable[[], Awaitable[Any]], *, ttl_seconds: float | None = None) -> Any:
        return await self.cache.run_singleflight(
            key,
            factory,
            ttl_seconds=ttl_seconds or self.TTL_SECONDS,
            workflow="intervention_analysis",
            resource=key.split(":")[-1],
        )
