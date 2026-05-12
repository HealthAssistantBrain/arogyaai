from __future__ import annotations

from ..models.score_snapshot import HealthScoreSnapshot
from .reasoning_engine import ReasoningEngine


class ScoreExplainer:
    @staticmethod
    def generate(snapshot: HealthScoreSnapshot) -> str:
        negatives = ReasoningEngine.top_negative_factors(snapshot, limit=2)
        if negatives:
            reasons = " and ".join(factor.summary.rstrip(".") for factor in negatives)
            return f"Your {snapshot.window} health score is {snapshot.trend} because {reasons.lower()}."
        if snapshot.trend == "improving":
            return "Your latest health score is improving as recovery, sleep, and physiological stability move in the right direction."
        if snapshot.trend == "deteriorating":
            return "Your latest health score is slipping as several physiological markers moved away from their recent baseline."
        return "Your latest health score is stable overall, with no major physiological shift detected in the current observation window."
