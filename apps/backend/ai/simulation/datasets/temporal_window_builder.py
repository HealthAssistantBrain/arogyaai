from __future__ import annotations

from typing import Any

from .._shared import log_simulation


class TemporalWindowBuilder:
    @staticmethod
    def build(vectors: list[dict[str, Any]], *, lookback_hours: int, horizon_hours: int) -> list[dict[str, Any]]:
        windows: list[dict[str, Any]] = []
        for start in range(0, max(0, len(vectors) - lookback_hours - horizon_hours + 1)):
            context = vectors[start : start + lookback_hours]
            future = vectors[start + lookback_hours : start + lookback_hours + horizon_hours]
            windows.append(
                {
                    "user_id": context[-1]["user_id"],
                    "window_start": context[0]["timestamp"],
                    "window_end": context[-1]["timestamp"],
                    "forecast_horizon_end": future[-1]["timestamp"],
                    "sequence": context,
                    "targets": {
                        "risk_target": future[-1]["risk_target"],
                        "future_recovery_target": future[-1]["future_recovery_target"],
                        "anomaly_target": max(item["anomaly_score"] for item in future),
                    },
                }
            )
        log_simulation("TEMPORAL WINDOW", count=len(windows), lookback=lookback_hours, horizon=horizon_hours)
        return windows
