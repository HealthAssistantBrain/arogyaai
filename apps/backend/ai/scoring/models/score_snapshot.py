from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ScoreFactor:
    name: str
    value: float | str | None
    impact: float
    direction: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "impact": self.impact,
            "direction": self.direction,
            "summary": self.summary,
        }


@dataclass(slots=True)
class ScoreMetric:
    name: str
    score: float
    confidence: float
    trend: str
    volatility: float
    baseline_delta: float
    anomaly_level: str
    factors: list[ScoreFactor] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "confidence": self.confidence,
            "trend": self.trend,
            "volatility": self.volatility,
            "baseline_delta": self.baseline_delta,
            "anomaly_level": self.anomaly_level,
            "factors": [factor.to_dict() for factor in self.factors],
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class HealthScoreSnapshot:
    user_id: str
    score: float
    confidence: float
    trend: str
    volatility: float
    baseline_delta: float
    anomaly_level: str
    generated_at: datetime
    window: str
    source: str
    explanation: str
    insight_headlines: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    category_scores: dict[str, ScoreMetric] = field(default_factory=dict)
    drivers: list[ScoreFactor] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "score": self.score,
            "confidence": self.confidence,
            "trend": self.trend,
            "volatility": self.volatility,
            "baseline_delta": self.baseline_delta,
            "anomaly_level": self.anomaly_level,
            "generated_at": self.generated_at.isoformat(),
            "window": self.window,
            "source": self.source,
            "explanation": self.explanation,
            "insight_headlines": self.insight_headlines,
            "recommendations": self.recommendations,
            "anomalies": self.anomalies,
            "category_scores": {
                name: metric.to_dict()
                for name, metric in self.category_scores.items()
            },
            "drivers": [driver.to_dict() for driver in self.drivers],
            "metadata": self.metadata,
        }
