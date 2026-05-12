from __future__ import annotations

from ..models.score_snapshot import ScoreFactor


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


class RecoveryScoreCalculator:
    @staticmethod
    def calculate(current: dict[str, float | None], recovery_signals: dict[str, float | None]) -> tuple[float, list[ScoreFactor], dict[str, float | None]]:
        recovery_proxy = float(recovery_signals.get("recovery_proxy") or current.get("recovery_proxy") or 68.0)
        sleep_hours = float(current.get("sleep_hours") or recovery_signals.get("baseline_sleep_hours") or 7.0)
        resting_hr = float(current.get("resting_hr") or recovery_signals.get("baseline_resting_hr") or 60.0)
        score = _clamp(recovery_proxy)
        factors = [
            ScoreFactor(
                name="recovery_proxy",
                value=round(recovery_proxy, 2),
                impact=round(recovery_proxy - 70.0, 3),
                direction="positive" if recovery_proxy >= 70.0 else "negative",
                summary="Recovery markers are supporting performance." if recovery_proxy >= 70.0 else "Recovery markers suggest your system is under load.",
            ),
            ScoreFactor(
                name="sleep_recovery_link",
                value=round(sleep_hours, 2),
                impact=round((sleep_hours - 7.0) * 8.0, 3),
                direction="positive" if sleep_hours >= 7.0 else "negative",
                summary="Sleep duration is helping recovery." if sleep_hours >= 7.0 else "Shorter sleep is limiting recovery.",
            ),
        ]
        return round(score, 3), factors, {"recovery_proxy": recovery_proxy, "sleep_hours": sleep_hours, "resting_hr": resting_hr}
