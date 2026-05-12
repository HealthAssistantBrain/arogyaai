from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

logger = logging.getLogger("resilience.retry")
T = TypeVar("T")


async def run_with_retry(
    factory: Callable[[], Awaitable[T]],
    *,
    operation: str,
    attempts: int = 2,
    backoff_seconds: Sequence[float] = (0.25,),
    retriable: Callable[[Exception], bool] | None = None,
) -> T:
    retriable = retriable or (lambda exc: True)
    max_attempts = max(1, int(attempts))
    delays = tuple(float(delay) for delay in backoff_seconds) or (0.0,)
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await factory()
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts or not retriable(exc):
                raise

            delay = delays[min(attempt - 1, len(delays) - 1)]
            logger.warning(
                "[RETRY] operation=%s attempt=%s/%s delay_seconds=%s error_type=%s error=%s",
                operation,
                attempt,
                max_attempts,
                round(delay, 3),
                exc.__class__.__name__,
                exc,
            )
            if delay > 0:
                await asyncio.sleep(delay)

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"{operation} retry policy exhausted without an error")
