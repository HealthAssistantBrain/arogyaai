from __future__ import annotations


class UncertaintyEngine:
    @staticmethod
    def estimate(
        *,
        confidence: float,
        volatility: float,
        sample_count: int,
    ) -> float:
        scarcity_penalty = 0.35 if sample_count < 5 else 0.18 if sample_count < 10 else 0.05
        uncertainty = (1.0 - max(0.0, min(1.0, confidence))) * 0.7 + min(0.5, volatility * 0.4) + scarcity_penalty
        return round(max(0.02, min(0.98, uncertainty)), 4)
