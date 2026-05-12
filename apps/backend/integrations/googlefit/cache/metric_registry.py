from __future__ import annotations

from dataclasses import dataclass

from .availability_cache import GoogleFitAvailabilityCache, MetricAvailabilityRecord
from .unsupported_metrics import (
    AVAILABILITY_REASON_DELAYED,
    AVAILABILITY_REASON_EMPTY,
    AVAILABILITY_REASON_UNAVAILABLE,
    AVAILABILITY_REASON_UNSUPPORTED,
)


@dataclass(frozen=True)
class MetricDescriptor:
    name: str
    optional: bool = False
    default_state: str = "supported"


METRIC_DESCRIPTORS = {
    "steps": MetricDescriptor(name="steps"),
    "heart_rate": MetricDescriptor(name="heart_rate"),
    "sleep": MetricDescriptor(name="sleep", optional=True),
    "spo2": MetricDescriptor(name="spo2", optional=True, default_state="unknown"),
    "glucose": MetricDescriptor(name="glucose", default_state="unknown"),
    "blood_pressure": MetricDescriptor(name="blood_pressure", default_state="unknown"),
    "body_temperature": MetricDescriptor(name="body_temperature", default_state="unknown"),
    "location": MetricDescriptor(name="location", optional=True, default_state="unknown"),
}

_STATE_BY_REASON = {
    AVAILABILITY_REASON_UNSUPPORTED: "unsupported",
    AVAILABILITY_REASON_UNAVAILABLE: "unavailable",
    AVAILABILITY_REASON_EMPTY: "empty",
    AVAILABILITY_REASON_DELAYED: "delayed",
}


class GoogleFitMetricRegistry:
    @classmethod
    def describe(cls, metric_name: str) -> MetricDescriptor:
        return METRIC_DESCRIPTORS.get(metric_name, MetricDescriptor(name=metric_name, default_state="unknown"))

    @classmethod
    async def current_state(cls, user_id: str, metric_name: str) -> tuple[str, MetricAvailabilityRecord | None]:
        record = await GoogleFitAvailabilityCache.get(user_id, metric_name)
        if record is None:
            return cls.describe(metric_name).default_state, None
        return _STATE_BY_REASON.get(record.reason, record.reason), record

    @classmethod
    async def should_query(cls, user_id: str, metric_name: str) -> tuple[bool, MetricAvailabilityRecord | None]:
        record = await GoogleFitAvailabilityCache.should_skip(user_id, metric_name)
        return record is None, record
