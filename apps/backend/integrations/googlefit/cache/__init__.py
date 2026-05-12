from .availability_cache import GoogleFitAvailabilityCache, MetricAvailabilityRecord
from .cooldown_manager import cooldown_seconds_for
from .metric_registry import GoogleFitMetricRegistry
from .unsupported_metrics import (
    AVAILABILITY_REASON_CIRCUIT_OPEN,
    AVAILABILITY_REASON_DELAYED,
    AVAILABILITY_REASON_EMPTY,
    AVAILABILITY_REASON_TIMEOUT,
    AVAILABILITY_REASON_UNAVAILABLE,
    AVAILABILITY_REASON_UNSUPPORTED,
    GoogleFitMetricAvailabilityError,
    classify_google_fit_failure,
)

__all__ = [
    "AVAILABILITY_REASON_CIRCUIT_OPEN",
    "AVAILABILITY_REASON_DELAYED",
    "AVAILABILITY_REASON_EMPTY",
    "AVAILABILITY_REASON_TIMEOUT",
    "AVAILABILITY_REASON_UNAVAILABLE",
    "AVAILABILITY_REASON_UNSUPPORTED",
    "GoogleFitAvailabilityCache",
    "GoogleFitMetricAvailabilityError",
    "GoogleFitMetricRegistry",
    "MetricAvailabilityRecord",
    "classify_google_fit_failure",
    "cooldown_seconds_for",
]
