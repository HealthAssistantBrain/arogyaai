from __future__ import annotations

from ..models.score_snapshot import ScoreFactor


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


class SleepScoreCalculator:
    @staticmethod
    def calculate(current: dict[str, float | None]) -> tuple[float, list[ScoreFactor], dict[str, float | None]]:
        sleep_hours = float(current.get("sleep_hours") or 0.0)
        efficiency = float(current.get("sleep_efficiency") or 0.0)
        duration_score = _clamp(100.0 - abs(sleep_hours - 8.0) * 18.0)
        efficiency_score = efficiency if efficiency > 0 else duration_score
        stability_bonus = 6.0 if 7.0 <= sleep_hours <= 8.5 else 0.0
        score = _clamp(duration_score * 0.55 + efficiency_score * 0.35 + stability_bonus)
        factors = [
            ScoreFactor(
                name="sleep_duration",
                value=round(sleep_hours, 2) if sleep_hours else None,
                impact=round(duration_score - 70.0, 3),
                direction="positive" if sleep_hours >= 7.0 else "negative",
                summary="Sleep duration is supporting recovery." if sleep_hours >= 7.0 else "Sleep duration is below the ideal recovery range.",
            ),
            ScoreFactor(
                name="sleep_efficiency",
                value=round(efficiency, 2) if efficiency else None,
                impact=round(efficiency_score - 70.0, 3),
                direction="positive" if efficiency_score >= 75.0 else "negative",
                summary="Sleep quality remained efficient." if efficiency_score >= 75.0 else "Sleep quality reduced the score.",
            ),
        ]
        return round(score, 3), factors, {"sleep_hours": sleep_hours or None, "sleep_efficiency": efficiency or None}
