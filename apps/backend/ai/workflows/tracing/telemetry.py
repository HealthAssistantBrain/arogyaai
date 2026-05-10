from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import threading
from typing import Any

from ..state.models import WorkflowExecutionContext


@dataclass(slots=True)
class ProviderLatencySample:
    provider: str
    latency_ms: float
    status: str


class WorkflowTelemetryStore:
    def __init__(self, *, max_recent_traces: int = 40) -> None:
        self._lock = threading.Lock()
        self._workflow_counters: dict[str, dict[str, float]] = defaultdict(
            lambda: {
                "total": 0,
                "success": 0,
                "fallback": 0,
                "timeout": 0,
                "latency_ms_total": 0.0,
                "retrieval_latency_ms_total": 0.0,
                "retrieval_count": 0,
                "retries_total": 0,
            }
        )
        self._provider_counters: dict[str, dict[str, float]] = defaultdict(
            lambda: {"attempts": 0, "success": 0, "latency_ms_total": 0.0}
        )
        self._formatter_counters: dict[str, dict[str, float]] = defaultdict(
            lambda: {
                "formatted": 0,
                "repairs": 0,
                "warnings": 0,
                "downgraded": 0,
                "failures": 0,
            }
        )
        self._recent_traces: deque[dict[str, Any]] = deque(maxlen=max_recent_traces)

    def record_workflow(
        self,
        workflow: str,
        *,
        latency_ms: float,
        retrieval_latency_ms: float | None,
        success: bool,
        fallback: bool,
        timed_out: bool,
        retries: int = 0,
    ) -> None:
        with self._lock:
            stats = self._workflow_counters[workflow]
            stats["total"] += 1
            stats["latency_ms_total"] += latency_ms
            stats["retries_total"] += max(retries, 0)
            if retrieval_latency_ms is not None:
                stats["retrieval_latency_ms_total"] += retrieval_latency_ms
                stats["retrieval_count"] += 1
            if success:
                stats["success"] += 1
            if fallback:
                stats["fallback"] += 1
            if timed_out:
                stats["timeout"] += 1

    def record_provider_attempts(self, attempts: list[ProviderLatencySample]) -> None:
        if not attempts:
            return
        with self._lock:
            for attempt in attempts:
                stats = self._provider_counters[attempt.provider]
                stats["attempts"] += 1
                stats["latency_ms_total"] += max(attempt.latency_ms, 0.0)
                if attempt.status == "ready":
                    stats["success"] += 1

    def record_trace(self, context: WorkflowExecutionContext, *, latency_ms: float) -> None:
        with self._lock:
            self._recent_traces.appendleft(
                {
                    "request_id": context.request_id,
                    "workflow": context.workflow,
                    "status": context.status,
                    "source": context.source,
                    "latency_ms": round(latency_ms, 2),
                    "fallback_activated": context.fallback_activated,
                    "route": context.orchestration_summary().get("route"),
                    "provider": context.provider_metadata.get("provider"),
                    "errors": list(context.errors[-3:]),
                }
            )

    def record_formatter_event(self, workflow: str, payload: dict[str, Any]) -> None:
        diagnostics = payload.get("formatter_diagnostics") if isinstance(payload.get("formatter_diagnostics"), dict) else {}
        warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
        with self._lock:
            stats = self._formatter_counters[workflow]
            stats["formatted"] += 1
            stats["warnings"] += len(warnings)
            stats["repairs"] += len(diagnostics.get("repairs_applied") or [])
            if diagnostics.get("validation_flags"):
                stats["downgraded"] += 1
            if payload.get("status") in {"failed", "error"}:
                stats["failures"] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            workflow_metrics = {}
            for workflow, stats in self._workflow_counters.items():
                total = max(stats["total"], 1)
                retrieval_count = max(stats["retrieval_count"], 1)
                workflow_metrics[workflow] = {
                    "workflow_count": int(stats["total"]),
                    "workflow_success_rate": round(stats["success"] / total, 4),
                    "workflow_latency_ms_avg": round(stats["latency_ms_total"] / total, 2),
                    "retrieval_latency_ms_avg": round(
                        stats["retrieval_latency_ms_total"] / retrieval_count,
                        2,
                    )
                    if stats["retrieval_count"]
                    else 0.0,
                    "timeout_frequency": round(stats["timeout"] / total, 4),
                    "fallback_frequency": round(stats["fallback"] / total, 4),
                    "retry_count_avg": round(stats["retries_total"] / total, 2),
                }

            provider_metrics = {}
            for provider, stats in self._provider_counters.items():
                attempts = max(stats["attempts"], 1)
                provider_metrics[provider] = {
                    "attempts": int(stats["attempts"]),
                    "success_rate": round(stats["success"] / attempts, 4),
                    "provider_latency_ms_avg": round(stats["latency_ms_total"] / attempts, 2),
                }

            formatter_metrics = {}
            for workflow, stats in self._formatter_counters.items():
                formatted = max(stats["formatted"], 1)
                formatter_metrics[workflow] = {
                    "formatted": int(stats["formatted"]),
                    "repair_rate": round(stats["repairs"] / formatted, 4),
                    "warning_rate": round(stats["warnings"] / formatted, 4),
                    "downgrade_rate": round(stats["downgraded"] / formatted, 4),
                    "formatter_failure_rate": round(stats["failures"] / formatted, 4),
                }

            traces = list(self._recent_traces)

        return {
            "workflows": workflow_metrics,
            "providers": provider_metrics,
            "formatter": formatter_metrics,
            "recent_traces": traces,
        }
