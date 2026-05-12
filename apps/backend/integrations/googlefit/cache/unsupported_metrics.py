from __future__ import annotations

AVAILABILITY_REASON_UNSUPPORTED = "unsupported"
AVAILABILITY_REASON_UNAVAILABLE = "unavailable"
AVAILABILITY_REASON_EMPTY = "empty"
AVAILABILITY_REASON_DELAYED = "delayed"
AVAILABILITY_REASON_TIMEOUT = "timeout"
AVAILABILITY_REASON_CIRCUIT_OPEN = "circuit_open"

_UNSUPPORTED_MARKERS = (
    "invalid_argument",
    "unsupported",
    "not supported",
    "no default data source",
    "no default datasource",
)
_UNAVAILABLE_MARKERS = (
    "data source does not exist",
    "datasource does not exist",
    "could not find data source",
    "no data source",
    "not found",
)


class GoogleFitMetricAvailabilityError(RuntimeError):
    def __init__(self, metric_name: str, reason: str, detail: str = "") -> None:
        super().__init__(f"{metric_name}:{reason}:{detail}")
        self.metric_name = metric_name
        self.reason = reason
        self.detail = detail

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.metric_name}:{self.reason}:{self.detail}"


def classify_google_fit_failure(*, detail: str | None = None, status_code: int | None = None) -> str | None:
    normalized = str(detail or "").strip().lower()
    if not normalized and status_code is None:
        return None
    if any(marker in normalized for marker in _UNSUPPORTED_MARKERS):
        return AVAILABILITY_REASON_UNSUPPORTED
    if any(marker in normalized for marker in _UNAVAILABLE_MARKERS):
        return AVAILABILITY_REASON_UNAVAILABLE
    if status_code == 400 and "data_source_id" in normalized:
        return AVAILABILITY_REASON_UNAVAILABLE
    return None
