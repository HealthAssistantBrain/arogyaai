from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("resilience.circuit_breaker")


class CircuitOpenError(RuntimeError):
    def __init__(self, name: str, retry_after_seconds: float) -> None:
        super().__init__(f"{name} circuit is open for another {retry_after_seconds:.1f}s")
        self.name = name
        self.retry_after_seconds = max(0.0, float(retry_after_seconds))


@dataclass
class _CircuitState:
    failures: int = 0
    opened_until: float | None = None
    last_failure_at: float | None = None
    half_open_inflight: bool = False


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 900.0,
    ) -> None:
        self.name = name
        self.failure_threshold = max(1, int(failure_threshold))
        self.recovery_timeout_seconds = max(1.0, float(recovery_timeout_seconds))
        self._state = _CircuitState()
        self._lock = threading.Lock()

    def before_call(self) -> None:
        now = time.monotonic()
        with self._lock:
            opened_until = self._state.opened_until
            if opened_until is None:
                return
            if now >= opened_until:
                if self._state.half_open_inflight:
                    raise CircuitOpenError(self.name, 0.0)
                self._state.half_open_inflight = True
                return
            raise CircuitOpenError(self.name, opened_until - now)

    def record_success(self) -> None:
        with self._lock:
            if self._state.opened_until is not None:
                logger.info("[CIRCUIT RECOVERED] name=%s", self.name)
            self._state = _CircuitState()

    def record_failure(self, exc: Exception) -> None:
        now = time.monotonic()
        with self._lock:
            self._state.failures += 1
            self._state.last_failure_at = now
            self._state.half_open_inflight = False
            if self._state.failures >= self.failure_threshold:
                self._state.opened_until = now + self.recovery_timeout_seconds
                logger.warning(
                    "[CIRCUIT OPEN] name=%s failures=%s retry_after_seconds=%s error_type=%s error=%s",
                    self.name,
                    self._state.failures,
                    round(self.recovery_timeout_seconds, 3),
                    exc.__class__.__name__,
                    exc,
                )


_BREAKERS: dict[str, CircuitBreaker] = {}
_BREAKERS_LOCK = threading.Lock()


def get_circuit_breaker(
    name: str,
    *,
    failure_threshold: int = 3,
    recovery_timeout_seconds: float = 900.0,
) -> CircuitBreaker:
    with _BREAKERS_LOCK:
        breaker = _BREAKERS.get(name)
        if breaker is None:
            breaker = CircuitBreaker(
                name,
                failure_threshold=failure_threshold,
                recovery_timeout_seconds=recovery_timeout_seconds,
            )
            _BREAKERS[name] = breaker
        return breaker
