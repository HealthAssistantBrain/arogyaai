from __future__ import annotations

from statistics import mean, pstdev


class VolatilityEngine:
    @staticmethod
    def score(values: list[float]) -> float:
        cleaned = [float(value) for value in values if value is not None]
        if len(cleaned) < 2:
            return 0.0
        series_mean = abs(mean(cleaned)) or 1.0
        coefficient = pstdev(cleaned) / series_mean
        return round(max(0.0, min(1.0, coefficient)), 4)
