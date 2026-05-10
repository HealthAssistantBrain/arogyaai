from __future__ import annotations

import threading
from collections import defaultdict, deque
from typing import Any


class ProviderTelemetryCollector:
    def __init__(self, *, max_recent_events: int = 80) -> None:
        self._lock = threading.Lock()
        self._events: deque[dict[str, Any]] = deque(maxlen=max_recent_events)
        self._provider_counters: dict[str, dict[str, float]] = defaultdict(
            lambda: {
                "attempts": 0,
                "success": 0,
                "fallbacks": 0,
                "streams": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "latency_ms_total": 0.0,
            }
        )

    def record(self, event: dict[str, Any]) -> None:
        provider = str(event.get("provider") or "unknown").strip()
        with self._lock:
            self._events.appendleft(dict(event))
            stats = self._provider_counters[provider]
            stats["attempts"] += 1
            stats["latency_ms_total"] += float(event.get("latency_ms") or 0.0)
            stats["tokens_in"] += int(event.get("tokens_in") or 0)
            stats["tokens_out"] += int(event.get("tokens_out") or 0)
            if event.get("status") == "ready":
                stats["success"] += 1
            if event.get("fallback_used"):
                stats["fallbacks"] += 1
            if event.get("streamed"):
                stats["streams"] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            providers: dict[str, Any] = {}
            for name, stats in self._provider_counters.items():
                attempts = max(1, int(stats["attempts"]))
                providers[name] = {
                    "attempts": int(stats["attempts"]),
                    "success_rate": round(float(stats["success"]) / attempts, 4),
                    "fallback_rate": round(float(stats["fallbacks"]) / attempts, 4),
                    "stream_rate": round(float(stats["streams"]) / attempts, 4),
                    "avg_latency_ms": round(float(stats["latency_ms_total"]) / attempts, 2),
                    "tokens_in": int(stats["tokens_in"]),
                    "tokens_out": int(stats["tokens_out"]),
                }
            return {
                "providers": providers,
                "recent_events": list(self._events),
            }
