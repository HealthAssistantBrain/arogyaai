from __future__ import annotations

from ..models.score_snapshot import ScoreFactor


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


class RespiratoryScoreCalculator:
    @staticmethod
    def calculate(current: dict[str, float | None]) -> tuple[float, list[ScoreFactor], dict[str, float | None]]:
        spo2 = float(current.get("spo2") or 97.0)
        resting_hr = float(current.get("resting_hr") or 60.0)
        spo2_score = _clamp((spo2 - 90.0) * 10.0)
        strain_penalty = max(0.0, resting_hr - 62.0) * 1.2
        score = _clamp(spo2_score - strain_penalty)
        factors = [
            ScoreFactor(
                name="spo2",
                value=round(spo2, 2),
                impact=round(spo2_score - 70.0, 3),
                direction="positive" if spo2 >= 96.0 else "negative",
                summary="Oxygen saturation is stable." if spo2 >= 96.0 else "Lower oxygen saturation reduced the respiratory score.",
            ),
        ]
        return round(score, 3), factors, {"spo2": spo2, "resting_hr": resting_hr}
