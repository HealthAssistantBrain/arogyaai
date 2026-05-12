from __future__ import annotations

from pydantic import BaseModel, Field

from .anomaly_response import AnomalyResponse
from .trend_metadata import TrendMetadata


class ScoreFactorResponse(BaseModel):
    name: str
    value: float | str | None = None
    impact: float = 0.0
    direction: str = "neutral"
    summary: str = ""


class ScoreMetricResponse(BaseModel):
    name: str
    score: float
    confidence: float
    trend: str
    volatility: float
    baseline_delta: float
    anomaly_level: str
    factors: list[ScoreFactorResponse] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ScoreResponse(BaseModel):
    score: float
    confidence: float
    trend: str
    volatility: float
    baseline_delta: float
    anomaly_level: str
    explanation: str
    window: str
    generated_at: str
    trend_metadata: TrendMetadata
    anomalies: list[AnomalyResponse] = Field(default_factory=list)
    category_scores: dict[str, ScoreMetricResponse] = Field(default_factory=dict)
    drivers: list[ScoreFactorResponse] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
