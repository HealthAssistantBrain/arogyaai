"""Canonical ingestion pipeline DTOs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


WearableMetricType = Literal[
    "heart_rate",
    "steps",
    "sleep",
    "spo2",
    "glucose",
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "body_temperature",
    "calories_burned",
]
WearableSource = Literal["google_fit", "apple_health", "fitbit", "oura", "manual"]


class WearableVitalRecord(BaseModel):
    """Validated wearable/vital time-series event."""

    model_config = ConfigDict(extra="allow")

    type: WearableMetricType
    value: float
    unit: str = Field(min_length=1, max_length=32)
    timestamp: datetime
    source: WearableSource = "google_fit"
    timezone: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp", mode="before")
    @classmethod
    def normalize_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, (int, float)):
            seconds = float(value)
            if seconds > 10_000_000_000:
                seconds /= 1000.0
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        raise ValueError("timestamp must be an ISO datetime or epoch value")

    @field_validator("type", "source", mode="before")
    @classmethod
    def normalize_label(cls, value: Any) -> str:
        return str(value or "").strip().lower()

    @model_validator(mode="after")
    def validate_metric_value(self) -> "WearableVitalRecord":
        if self.value < 0:
            raise ValueError("wearable metric value cannot be negative")
        if self.value == 0 and self.type not in {"steps", "calories_burned"}:
            raise ValueError("zero values are only accepted for cumulative metrics")
        return self

    def to_storage_dict(self) -> dict[str, Any]:
        payload = self.model_dump()
        payload["timestamp"] = self.timestamp.astimezone(timezone.utc)
        return payload


class IngestionPipelineRequest(BaseModel):
    user_id: str
    device_type: str | None = None
    source: WearableSource = "google_fit"
    records: list[WearableVitalRecord] = Field(default_factory=list)


class IngestionPipelineResponse(BaseModel):
    success: bool = True
    status: str = "ready"
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
