from __future__ import annotations

from typing import Any

from ..core.weighting_engine import WeightingEngine


class HealthScoreCalculator:
    @staticmethod
    def calculate(
        category_scores: dict[str, float | None],
        *,
        trend_consistency: float,
        anomaly_count: int,
    ) -> tuple[float, dict[str, Any]]:
        return WeightingEngine.combine(
            category_scores=category_scores,
            trend_consistency=trend_consistency,
            anomaly_count=anomaly_count,
        )
