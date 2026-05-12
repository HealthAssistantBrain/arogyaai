from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .prediction_metadata import PredictionMetadata, ProjectionContributor
from .trajectory_response import PreventiveAlertResponse, TrajectoryResponse


class DomainForecastResponse(BaseModel):
    domain: str
    window: str
    projected_value: float = 0.0
    projected_score: float = 0.0
    projected_risk: float = 0.0
    current_risk: float = 0.0
    baseline_delta: float = 0.0
    direction: str = "stable"
    explanation: str = ""
    recommendation: str = ""
    confidence: float = 0.0
    uncertainty: float = 1.0
    projection_strength: float = 0.0
    signal_quality: float = 0.0
    stability: float = 0.0
    volatility: float = 0.0
    contributors: list[ProjectionContributor] = Field(default_factory=list)
    metadata: PredictionMetadata = Field(default_factory=PredictionMetadata)


class ForecastWindowResponse(BaseModel):
    window: str
    horizon_days: int
    overall_outlook: str
    summary: str
    explanation: str
    confidence: float = 0.0
    uncertainty: float = 1.0
    projection_strength: float = 0.0
    signal_quality: float = 0.0
    stability: float = 0.0
    domains: list[DomainForecastResponse] = Field(default_factory=list)
    predictions: list[DomainForecastResponse] = Field(default_factory=list)
    trajectories: list[TrajectoryResponse] = Field(default_factory=list)
    alerts: list[PreventiveAlertResponse] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ForecastResponse(BaseModel):
    user_id: str
    generated_at: str
    source: str = "predictive_forecasting_engine"
    status: str = "ready"
    summary: str = ""
    forecast: dict[str, ForecastWindowResponse] = Field(default_factory=dict)
    confidence: float = 0.0
    uncertainty: float = 1.0
    projection_strength: float = 0.0
    signal_quality: float = 0.0
    stability: float = 0.0
    forecast_history: list[dict[str, Any]] = Field(default_factory=list)
    memory_context: list[str] = Field(default_factory=list)
    safety: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
