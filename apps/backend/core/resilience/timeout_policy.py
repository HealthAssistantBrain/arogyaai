from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger("resilience.timeout")
T = TypeVar("T")


class TimeoutPolicyError(asyncio.TimeoutError):
    def __init__(self, operation: str, timeout_seconds: float) -> None:
        super().__init__(f"{operation} exceeded timeout budget of {timeout_seconds:.2f}s")
        self.operation = operation
        self.timeout_seconds = float(timeout_seconds)


async def run_with_timeout(
    awaitable: Awaitable[T],
    *,
    timeout_seconds: float,
    operation: str,
    on_timeout: Callable[[], T] | None = None,
) -> T:
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        logger.warning(
            "[TIMEOUT] operation=%s timeout_seconds=%s",
            operation,
            round(float(timeout_seconds), 3),
        )
        if on_timeout is not None:
            return on_timeout()
        raise TimeoutPolicyError(operation, timeout_seconds) from exc
