from __future__ import annotations

from datetime import datetime
from typing import Any


class SensorFailureSimulator:
    @staticmethod
    def apply(points: list[dict[str, Any]], affected_metrics: list[str], start: datetime, duration_hours: int) -> None:
        end = start.timestamp() + duration_hours * 3600
        for point in points:
            ts = point["timestamp"].timestamp()
            if start.timestamp() <= ts < end:
                for metric in affected_metrics:
                    point[metric] = None
                point.setdefault("sensor_failures", []).extend(affected_metrics)
