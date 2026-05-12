from __future__ import annotations

from ..models.score_snapshot import ScoreFactor


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


class StressScoreCalculator:
    @staticmethod
    def calculate(current: dict[str, float | None], baseline: dict[str, float | None]) -> tuple[float, list[ScoreFactor], dict[str, float | None]]:
        stress_level = float(current.get("stress_level") or 4.0)
        resting_hr = float(current.get("resting_hr") or baseline.get("resting_hr") or 60.0)
        hrv = float(current.get("hrv") or baseline.get("hrv") or 48.0)
        baseline_rhr = float(baseline.get("resting_hr") or 60.0)
        baseline_hrv = float(baseline.get("hrv") or 48.0)
        explicit_component = 100.0 - max(0.0, stress_level - 1.0) * 11.0
        rhr_component = 100.0 - max(0.0, resting_hr - baseline_rhr) * 3.2
        hrv_component = 100.0 - max(0.0, baseline_hrv - hrv) * 1.7
        score = _clamp(explicit_component * 0.4 + rhr_component * 0.3 + hrv_component * 0.3)
        factors = [
            ScoreFactor(
                name="stress_level",
                value=round(stress_level, 2),
                impact=round(explicit_component - 70.0, 3),
                direction="positive" if stress_level <= 4.0 else "negative",
                summary="Self-reported stress is manageable." if stress_level <= 4.0 else "Stress burden is elevated.",
            ),
            ScoreFactor(
                name="hrv_resilience",
                value=round(hrv, 2),
                impact=round(hrv_component - 70.0, 3),
                direction="positive" if hrv >= baseline_hrv else "negative",
                summary="HRV suggests good resilience." if hrv >= baseline_hrv else "Reduced HRV is consistent with higher physiological stress.",
            ),
        ]
        return round(score, 3), factors, {"stress_level": stress_level, "resting_hr": resting_hr, "hrv": hrv}
