from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

logger = logging.getLogger("startup_lifecycle")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ServiceState:
    name: str
    tier: str
    blocking: bool = False
    status: str = "pending"
    detail: str | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: float | None = None
    updated_at: str | None = None


class StartupLifecycle:
    def __init__(self) -> None:
        self._services: dict[str, ServiceState] = {}
        self._tasks: set[asyncio.Task[Any]] = set()
        self._phase = "cold"
        self._started_at = _utc_now()
        self.reset()

    def reset(self) -> None:
        self._phase = "cold"
        self._started_at = _utc_now()
        self._services = {
            "core_api": ServiceState("core_api", "tier1", blocking=True),
            "db": ServiceState("db", "tier1", blocking=True),
            "auth": ServiceState("auth", "tier1", blocking=True),
            "redis": ServiceState("redis", "tier1", blocking=True),
            "analytics_db": ServiceState("analytics_db", "tier2"),
            "timescale": ServiceState("timescale", "tier2"),
            "supabase_auth": ServiceState("supabase_auth", "tier2"),
            "prediction_service": ServiceState("prediction_service", "tier2"),
            "rag_service": ServiceState("rag_service", "tier2"),
            "qdrant": ServiceState("qdrant", "tier2"),
            "ollama": ServiceState("ollama", "tier2"),
            "nvidia_provider": ServiceState("nvidia_provider", "tier2"),
            "memory": ServiceState("memory", "tier2"),
            "google_fit_worker": ServiceState("google_fit_worker", "tier3"),
            "dashboard_listener": ServiceState("dashboard_listener", "tier3"),
            "emergency_worker": ServiceState("emergency_worker", "tier3"),
        }
        for task in list(self._tasks):
            task.cancel()
        self._tasks.clear()

    def set_phase(self, phase: str) -> None:
        self._phase = phase

    def mark(
        self,
        service_name: str,
        *,
        status: str,
        detail: str | None = None,
        error: str | None = None,
        duration_ms: float | None = None,
    ) -> None:
        service = self._services.setdefault(service_name, ServiceState(service_name, "tier3"))
        now = _utc_now()
        if service.started_at is None and status in {"running", "warming", "deferred"}:
            service.started_at = now
        if status in {"ready", "healthy", "degraded", "failed", "skipped"}:
            service.completed_at = now
        service.status = status
        service.detail = detail
        service.error = error
        service.duration_ms = duration_ms
        service.updated_at = now

    async def run_blocking(
        self,
        service_name: str,
        task_factory: Callable[[], Awaitable[Any]],
        *,
        detail: str | None = None,
    ) -> Any:
        started_at = time.perf_counter()
        self.mark(service_name, status="running", detail=detail)
        try:
            result = await task_factory()
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            self.mark(service_name, status="ready", detail=detail or "ready", duration_ms=duration_ms)
            return result
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            self.mark(service_name, status="degraded", detail=detail or "degraded", error=str(exc), duration_ms=duration_ms)
            raise

    def schedule(
        self,
        service_name: str,
        task_factory: Callable[[], Awaitable[Any]],
        *,
        delay_seconds: float = 0.0,
        timeout_seconds: float = 30.0,
        detail: str | None = None,
    ) -> asyncio.Task[Any]:
        async def _runner() -> None:
            if delay_seconds > 0:
                self.mark(service_name, status="deferred", detail=f"scheduled_in_{round(delay_seconds, 1)}s")
                await asyncio.sleep(delay_seconds)

            started_at = time.perf_counter()
            self.mark(service_name, status="warming", detail=detail or "warming")
            try:
                result = await asyncio.wait_for(task_factory(), timeout=timeout_seconds)
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
                next_status = "ready"
                detail_message = detail or "ready"
                if isinstance(result, dict):
                    next_status = str(result.get("status") or "ready")
                    detail_message = str(result.get("detail") or result.get("status") or detail_message)
                self.mark(service_name, status=next_status, detail=detail_message, duration_ms=duration_ms)
            except asyncio.TimeoutError:
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
                self.mark(service_name, status="degraded", detail="timeout", error="startup_timeout", duration_ms=duration_ms)
                logger.warning("[StartupLifecycle] %s timed out after %ss", service_name, timeout_seconds)
            except asyncio.CancelledError:
                self.mark(service_name, status="skipped", detail="cancelled")
                raise
            except Exception as exc:
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
                self.mark(service_name, status="degraded", detail="failed", error=str(exc), duration_ms=duration_ms)
                logger.exception("[StartupLifecycle] %s failed: %s", service_name, exc)

        task = asyncio.create_task(_runner(), name=f"startup-lifecycle:{service_name}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def shutdown(self) -> None:
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    def snapshot(self) -> dict[str, Any]:
        services = {
            name: {
                "tier": state.tier,
                "blocking": state.blocking,
                "status": state.status,
                "detail": state.detail,
                "error": state.error,
                "started_at": state.started_at,
                "completed_at": state.completed_at,
                "duration_ms": state.duration_ms,
                "updated_at": state.updated_at,
            }
            for name, state in self._services.items()
        }
        return {
            "phase": self._phase,
            "started_at": self._started_at,
            "updated_at": _utc_now(),
            "services": services,
        }


startup_lifecycle = StartupLifecycle()
