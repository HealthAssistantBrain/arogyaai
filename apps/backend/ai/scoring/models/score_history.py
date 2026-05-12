from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ScoreHistoryPoint:
    timestamp: datetime
    score: float
    confidence: float
    trend: str
    volatility: float
    anomaly_level: str
    source: str = "scoring"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "score": self.score,
            "confidence": self.confidence,
            "trend": self.trend,
            "volatility": self.volatility,
            "anomaly_level": self.anomaly_level,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class ScoreHistory:
    user_id: str
    range_key: str
    points: list[ScoreHistoryPoint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "range": self.range_key,
            "points": [point.to_dict() for point in self.points],
        }
