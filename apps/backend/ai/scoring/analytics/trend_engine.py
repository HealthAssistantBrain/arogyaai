from __future__ import annotations

from statistics import mean


def _safe_mean(values: list[float]) -> float | None:
    cleaned = [float(value) for value in values if value is not None]
    if not cleaned:
        return None
    return float(mean(cleaned))


class TrendEngine:
    @staticmethod
    def classify(
        values: list[float],
        *,
        lower_is_better: bool = False,
        recovery_hint: bool = False,
    ) -> dict[str, float | str]:
        cleaned = [float(value) for value in values if value is not None]
        if len(cleaned) < 2:
            return {
                "direction": "stable",
                "slope": 0.0,
                "change_percent": 0.0,
                "consistency": 0.0,
            }

        split_index = max(1, len(cleaned) // 2)
        previous_mean = _safe_mean(cleaned[:split_index]) or cleaned[0]
        recent_mean = _safe_mean(cleaned[split_index:]) or cleaned[-1]
        slope = recent_mean - previous_mean
        denominator = abs(previous_mean) if abs(previous_mean) > 0.01 else 1.0
        change_percent = (slope / denominator) * 100.0
        average_step_change = sum(
            abs(cleaned[index] - cleaned[index - 1])
            for index in range(1, len(cleaned))
        ) / max(1, len(cleaned) - 1)
        amplitude = max(cleaned) - min(cleaned)
        consistency = max(0.0, min(1.0, 1.0 - (average_step_change / max(amplitude, 1.0))))

        effective_change = -change_percent if lower_is_better else change_percent
        if consistency < 0.35 and amplitude >= max(6.0, abs(previous_mean) * 0.08):
            direction = "volatile"
        elif recovery_hint and effective_change <= -5.0:
            direction = "recovery-needed"
        elif abs(change_percent) <= 2.5:
            direction = "stable"
        elif effective_change >= 5.0:
            direction = "improving"
        else:
            direction = "deteriorating"

        return {
            "direction": direction,
            "slope": round(slope, 3),
            "change_percent": round(change_percent, 3),
            "consistency": round(consistency, 3),
        }
