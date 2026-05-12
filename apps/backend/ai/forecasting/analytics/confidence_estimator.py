from __future__ import annotations


class ConfidenceEstimator:
    @staticmethod
    def estimate(
        *,
        sample_count: int,
        baseline_available: bool,
        stability: float,
        volatility: float,
        source_count: int,
    ) -> float:
        sample_component = min(1.0, max(0.0, sample_count) / 18.0)
        baseline_component = 1.0 if baseline_available else 0.45
        source_component = min(1.0, max(0.0, source_count) / 4.0)
        volatility_penalty = min(0.45, max(0.0, volatility) * 0.35)
        confidence = (
            sample_component * 0.35
            + baseline_component * 0.2
            + max(0.0, stability) * 0.25
            + source_component * 0.2
            - volatility_penalty
        )
        return round(max(0.08, min(0.98, confidence)), 4)
