from __future__ import annotations

from statistics import pstdev


class ProjectionVolatility:
    @staticmethod
    def score(values: list[float]) -> float:
        cleaned = [float(value) for value in values if value is not None]
        if len(cleaned) < 2:
            return 0.0
        deviation = float(pstdev(cleaned))
        amplitude = max(cleaned) - min(cleaned)
        normalizer = max(6.0, amplitude, abs(sum(cleaned) / len(cleaned)) * 0.15, 1.0)
        return round(max(0.0, min(1.0, deviation / normalizer)), 4)
