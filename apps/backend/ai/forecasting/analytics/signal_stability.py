from __future__ import annotations


class SignalStability:
    @staticmethod
    def score(values: list[float]) -> float:
        cleaned = [float(value) for value in values if value is not None]
        if len(cleaned) < 2:
            return 0.35
        step_change = sum(abs(cleaned[index] - cleaned[index - 1]) for index in range(1, len(cleaned))) / max(1, len(cleaned) - 1)
        amplitude = max(cleaned) - min(cleaned)
        if amplitude <= 0:
            return 1.0
        stability = 1.0 - (step_change / max(amplitude, 1.0))
        return round(max(0.0, min(1.0, stability)), 4)
