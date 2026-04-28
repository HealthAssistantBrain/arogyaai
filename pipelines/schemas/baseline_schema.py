from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pipelines.storage_pipeline.utils import serialize_for_json


def _normalize_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class BaselineMetricDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    metric_name: str = Field(min_length=1)
    mean_7d: float | None = None
    mean_30d: float | None = None
    std_dev: float | None = None
    sample_count: int = Field(default=0, ge=0)
    window_start: datetime | None = None
    window_end: datetime | None = None
    metric_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metric_name")
    @classmethod
    def _validate_metric_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("metric_name must not be blank")
        return cleaned

    @field_validator("window_start", "window_end", mode="before")
    @classmethod
    def _validate_window(cls, value: Any) -> Any:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return _normalize_utc_datetime(value)
        return value

    def to_storage_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")

    def to_json_dict(self) -> dict[str, Any]:
        return serialize_for_json(self.to_storage_dict())
