from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from typing import Any


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class ProviderHealthMonitor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.cooldown_seconds = _env_float("AI_PROVIDER_HEALTH_COOLDOWN_SECONDS", 45.0)
        self.max_consecutive_failures = int(_env_float("AI_PROVIDER_HEALTH_MAX_CONSECUTIVE_FAILURES", 3))
        self.latency_budget_ms = _env_float("AI_PROVIDER_LATENCY_BUDGET_MS", 8000.0)
        self._stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "attempts": 0,
                "success": 0,
                "failures": 0,
                "timeouts": 0,
                "retries": 0,
                "consecutive_failures": 0,
                "latencies_ms": deque(maxlen=25),
                "degraded": False,
                "quarantined_until": 0.0,
                "last_error": None,
                "last_checked_at": None,
            }
        )

    def is_quarantined(self, provider: str) -> bool:
        with self._lock:
            return float(self._stats[provider]["quarantined_until"]) > time.monotonic()

    def score(self, provider: str) -> float:
        with self._lock:
            stats = self._stats[provider]
            attempts = max(1, int(stats["attempts"]))
            success_rate = float(stats["success"]) / attempts
            latency_values = list(stats["latencies_ms"])
            avg_latency = (sum(latency_values) / len(latency_values)) if latency_values else 0.0
            latency_penalty = min(0.45, avg_latency / max(self.latency_budget_ms, 1.0))
            degraded_penalty = 0.25 if stats["degraded"] else 0.0
            quarantine_penalty = 0.5 if float(stats["quarantined_until"]) > time.monotonic() else 0.0
            return round(max(0.0, min(1.0, success_rate - latency_penalty - degraded_penalty - quarantine_penalty)), 4)

    def record_attempt(
        self,
        provider: str,
        *,
        status: str,
        latency_ms: float,
        error: str | None = None,
        retry_count: int = 0,
    ) -> None:
        with self._lock:
            stats = self._stats[provider]
            stats["attempts"] += 1
            stats["retries"] += max(0, retry_count)
            stats["last_checked_at"] = time.time()
            stats["latencies_ms"].append(max(0.0, float(latency_ms or 0.0)))
            if status == "ready":
                stats["success"] += 1
                stats["consecutive_failures"] = 0
                stats["degraded"] = False
                stats["quarantined_until"] = 0.0
                stats["last_error"] = None
                return

            stats["failures"] += 1
            stats["consecutive_failures"] += 1
            stats["last_error"] = error
            if status == "timeout":
                stats["timeouts"] += 1
            if stats["consecutive_failures"] >= self.max_consecutive_failures:
                stats["degraded"] = True
                stats["quarantined_until"] = time.monotonic() + self.cooldown_seconds

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            payload: dict[str, Any] = {}
            now = time.monotonic()
            for provider, stats in self._stats.items():
                latencies = list(stats["latencies_ms"])
                attempts = max(1, int(stats["attempts"]))
                payload[provider] = {
                    "attempts": int(stats["attempts"]),
                    "success_rate": round(float(stats["success"]) / attempts, 4),
                    "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
                    "failure_rate": round(float(stats["failures"]) / attempts, 4),
                    "timeout_frequency": round(float(stats["timeouts"]) / attempts, 4),
                    "retry_count": int(stats["retries"]),
                    "degraded": bool(stats["degraded"]),
                    "quarantined": float(stats["quarantined_until"]) > now,
                    "quarantined_until": stats["quarantined_until"] if float(stats["quarantined_until"]) > now else None,
                    "last_error": stats["last_error"],
                    "score": self.score(provider),
                }
            return payload
