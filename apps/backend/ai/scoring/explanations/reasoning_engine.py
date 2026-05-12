from __future__ import annotations

from ..models.score_snapshot import HealthScoreSnapshot, ScoreFactor


class ReasoningEngine:
    @staticmethod
    def top_negative_factors(snapshot: HealthScoreSnapshot, limit: int = 3) -> list[ScoreFactor]:
        candidates: list[ScoreFactor] = []
        for metric in snapshot.category_scores.values():
            candidates.extend(metric.factors)
        candidates.extend(snapshot.drivers)
        negatives = [
            factor for factor in candidates
            if factor.impact < 0
        ]
        negatives.sort(key=lambda item: item.impact)
        return negatives[:limit]
