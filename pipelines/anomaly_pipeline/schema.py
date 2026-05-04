from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnomalySignal(BaseModel):
    metric: str
    value: float
    baseline: float
    robust_z_score: float
    direction: str
    severity: str = Field(pattern="^(warning|critical)$")
    title: str
    message: str
    observed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnomalyDetectionRequest(BaseModel):
    user_id: str
    vital_types: list[str] | None = None
    lookback_days: int = Field(default=30, ge=1, le=180)
    min_points: int = Field(default=6, ge=3, le=100)


class AnomalyDetectionResponse(BaseModel):
    success: bool = True
    status: str = "ready"
    source: str = "robust_baseline"
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
