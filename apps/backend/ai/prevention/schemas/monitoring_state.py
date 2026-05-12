from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..utils import utc_now


class MonitoringSignal(BaseModel):
    signal_id: str
    domain: str
    kind: str
    severity: str = "info"
    risk_score: float = 0.0
    confidence: float = 0.0
    direction: str = "stable"
    summary: str
    value: float | None = None
    baseline_delta: float | None = None
    persistence_days: float = 0.0
    acceleration: float = 0.0
    monitor: str
    supporting_metrics: dict[str, Any] = Field(default_factory=dict)
    recommended_actions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class MonitoringState(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    status: str = "ready"
    overall_risk: float = 0.0
    dominant_severity: str = "info"
    summary: str = ""
    signals: list[MonitoringSignal] = Field(default_factory=list)
    domain_risk: dict[str, float] = Field(default_factory=dict)
    risk_counts: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
