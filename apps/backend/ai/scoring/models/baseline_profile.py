from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class BaselineMetricProfile:
    metric_name: str
    mean_7d: float | None = None
    mean_30d: float | None = None
    std_dev: float | None = None
    sample_count: int = 0
    window_start: datetime | None = None
    window_end: datetime | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def reference(self) -> float | None:
        return self.mean_7d if self.mean_7d is not None else self.mean_30d

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "mean_7d": self.mean_7d,
            "mean_30d": self.mean_30d,
            "std_dev": self.std_dev,
            "sample_count": self.sample_count,
            "window_start": self.window_start.isoformat() if self.window_start else None,
            "window_end": self.window_end.isoformat() if self.window_end else None,
            "payload": self.payload,
        }


@dataclass(slots=True)
class BaselineProfile:
    user_id: str
    generated_at: datetime
    metrics: dict[str, BaselineMetricProfile] = field(default_factory=dict)

    def get(self, metric_name: str) -> BaselineMetricProfile | None:
        return self.metrics.get(metric_name)

    def reference_value(self, metric_name: str, fallback: float | None = None) -> float | None:
        metric = self.get(metric_name)
        if metric is None or metric.reference is None:
            return fallback
        return metric.reference

    def std_dev(self, metric_name: str, fallback: float | None = None) -> float | None:
        metric = self.get(metric_name)
        if metric is None or metric.std_dev is None:
            return fallback
        return metric.std_dev

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "generated_at": self.generated_at.isoformat(),
            "metrics": {
                name: metric.to_dict()
                for name, metric in self.metrics.items()
            },
        }
