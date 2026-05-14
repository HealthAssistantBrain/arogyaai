from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SyntheticSnapshot(BaseModel):
    user_id: str
    timestamp: datetime
    signal_type: str
    signal_name: str
    value: float | None = None
    unit: str
    confidence: float = 1.0
    baseline_delta: float = 0.0
    anomaly_score: float = 0.0
    risk_level: str = "low"
    physiological_state: str = "stable"
    recovery_state: str = "stable"
    trend_direction: str = "stable"
    synthetic_profile: str
    demographic_profile: str
    trajectory_phase: str = "stable"
    source: str = "synthetic_simulation_engine"
    labels: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
