from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Awaitable, Callable

from core.resilience.circuit_breaker import CircuitOpenError, get_circuit_breaker
from core.resilience.retry_policy import run_with_retry

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - optional dependency fallback
    Redis = None  # type: ignore[assignment]

logger = logging.getLogger("redis_resilience")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()
REDIS_CONNECT_TIMEOUT_SECONDS = max(0.1, float(os.getenv("REDIS_CONNECT_TIMEOUT_SECONDS", "0.5")))
REDIS_SOCKET_TIMEOUT_SECONDS = max(0.1, float(os.getenv("REDIS_SOCKET_TIMEOUT_SECONDS", "0.5")))
REDIS_RETRY_ATTEMPTS = max(1, int(os.getenv("REDIS_RETRY_ATTEMPTS", "3")))
REDIS_RETRY_BACKOFF_SECONDS = (
    0.1,
    0.25,
    0.5,
)
REDIS_CIRCUIT_FAILURE_THRESHOLD = max(1, int(os.getenv("REDIS_CIRCUIT_FAILURE_THRESHOLD", "3")))
REDIS_CIRCUIT_RECOVERY_SECONDS = max(1.0, float(os.getenv("REDIS_CIRCUIT_RECOVERY_SECONDS", "15.0")))


class RedisCircuitBreaker:
    def __init__(self, name: str) -> None:
        self.name = name
        self._breaker = get_circuit_breaker(
            f"redis:{name}",
            failure_threshold=REDIS_CIRCUIT_FAILURE_THRESHOLD,
            recovery_timeout_seconds=REDIS_CIRCUIT_RECOVERY_SECONDS,
        )
        self._degraded = False
        self._lock = asyncio.Lock()

    async def call(
        self,
        operation: str,
        factory: Callable[[], Awaitable[Any]],
    ) -> Any:
        try:
            self._breaker.before_call()
        except CircuitOpenError as exc:
            logger.warning(
                "[REDIS DEGRADED] name=%s operation=%s retry_after_seconds=%s",
                self.name,
                operation,
                round(exc.retry_after_seconds, 3),
            )
            raise

        try:
            result = await run_with_retry(
                factory,
                operation=f"redis:{self.name}:{operation}",
                attempts=REDIS_RETRY_ATTEMPTS,
                backoff_seconds=REDIS_RETRY_BACKOFF_SECONDS,
            )
        except Exception as exc:
            self._breaker.record_failure(exc)
            async with self._lock:
                self._degraded = True
            logger.warning(
                "[REDIS DEGRADED] name=%s operation=%s error_type=%s error=%s",
                self.name,
                operation,
                exc.__class__.__name__,
                exc,
            )
            raise

        self._breaker.record_success()
        async with self._lock:
            if self._degraded:
                logger.info("[REDIS RECOVERY] name=%s operation=%s", self.name, operation)
                logger.info("[REDIS RECONNECTED] name=%s operation=%s", self.name, operation)
            self._degraded = False
        return result


class ResilientRedisPool:
    def __init__(self, name: str, *, url: str | None = None) -> None:
        self.name = name
        self.url = (url or REDIS_URL).strip()
        self._client: Redis | None = None
        self._client_lock = asyncio.Lock()
        self._breaker = RedisCircuitBreaker(name)

    async def call(
        self,
        operation: str,
        callback: Callable[[Redis], Awaitable[Any]],
    ) -> Any:
        async def _invoke() -> Any:
            client = await self._get_client()
            if client is None:
                raise RuntimeError("redis_client_unavailable")
            return await callback(client)

        return await self._breaker.call(operation, _invoke)

    async def ping(self) -> dict[str, Any]:
        return await self.call(
            "ping",
            lambda client: client.ping(),
        )

    async def close(self) -> None:
        async with self._client_lock:
            client = self._client
            self._client = None
        if isinstance(client, Redis):
            try:
                await client.aclose()
            except Exception:
                logger.debug("[REDIS CLOSE FAILED] name=%s", self.name, exc_info=True)

    async def _get_client(self) -> Redis | None:
        if not self.url or Redis is None:
            return None

        async with self._client_lock:
            if isinstance(self._client, Redis):
                return self._client

            try:
                self._client = Redis.from_url(
                    self.url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=REDIS_CONNECT_TIMEOUT_SECONDS,
                    socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
                    health_check_interval=30,
                )
            except Exception:
                logger.warning("[REDIS DEGRADED] name=%s operation=create_client", self.name, exc_info=True)
                self._client = None
                return None
            return self._client


_POOLS: dict[str, ResilientRedisPool] = {}
_POOLS_LOCK = asyncio.Lock()


async def get_resilient_redis_pool(name: str, *, url: str | None = None) -> ResilientRedisPool:
    async with _POOLS_LOCK:
        pool = _POOLS.get(name)
        if pool is None:
            pool = ResilientRedisPool(name, url=url)
            _POOLS[name] = pool
        return pool
