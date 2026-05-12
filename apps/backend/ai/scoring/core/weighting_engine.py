from __future__ import annotations

from typing import Any


class WeightingEngine:
    DEFAULT_WEIGHTS = {
        "cardiovascular_score": 0.24,
        "metabolic_score": 0.18,
        "sleep_score": 0.17,
        "stress_score": 0.14,
        "recovery_score": 0.16,
        "respiratory_score": 0.11,
    }

    @staticmethod
    def combine(
        *,
        category_scores: dict[str, float | None],
        trend_consistency: float,
        anomaly_count: int,
    ) -> tuple[float, dict[str, Any]]:
        available = {
            name: float(score)
            for name, score in category_scores.items()
            if score is not None
        }
        if not available:
            return 0.0, {"components": {}, "trend_consistency": trend_consistency, "anomaly_penalty": 0.0}

        active_weights = {
            name: WeightingEngine.DEFAULT_WEIGHTS.get(name, 0.0)
            for name in available
        }
        total_weight = sum(active_weights.values()) or 1.0
        normalized_weights = {
            name: weight / total_weight
            for name, weight in active_weights.items()
        }
        weighted_score = sum(
            available[name] * normalized_weights[name]
            for name in available
        )
        trend_bonus = max(-4.0, min(4.0, (trend_consistency - 0.5) * 8.0))
        anomaly_penalty = min(12.0, float(anomaly_count) * 3.0)
        final_score = max(0.0, min(100.0, weighted_score + trend_bonus - anomaly_penalty))
        components = {
            name: {
                "score": available[name],
                "weight": round(normalized_weights[name], 4),
                "weighted_contribution": round(available[name] * normalized_weights[name], 4),
            }
            for name in available
        }
        return round(final_score, 3), {
            "components": components,
            "trend_consistency": round(trend_consistency, 4),
            "trend_bonus": round(trend_bonus, 4),
            "anomaly_penalty": round(anomaly_penalty, 4),
        }
