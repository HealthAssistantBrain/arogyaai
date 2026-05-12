from __future__ import annotations

from ..models.score_snapshot import ScoreFactor


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


class CardiovascularScoreCalculator:
    @staticmethod
    def calculate(current: dict[str, float | None], baseline: dict[str, float | None]) -> tuple[float, list[ScoreFactor], dict[str, float | None]]:
        systolic = float(current.get("blood_pressure_systolic") or baseline.get("blood_pressure_systolic") or 118.0)
        diastolic = float(current.get("blood_pressure_diastolic") or baseline.get("blood_pressure_diastolic") or 76.0)
        resting_hr = float(current.get("resting_hr") or baseline.get("resting_hr") or 60.0)
        hrv = float(current.get("hrv") or baseline.get("hrv") or 48.0)
        steps = float(current.get("activity_steps") or baseline.get("activity_steps") or 7000.0)
        bp_score = _clamp(100.0 - max(0.0, systolic - 118.0) * 1.2 - max(0.0, diastolic - 76.0) * 1.4)
        hr_score = _clamp(100.0 - max(0.0, resting_hr - 58.0) * 2.6)
        hrv_score = _clamp(45.0 + hrv * 0.9)
        activity_score = _clamp((steps / 10000.0) * 100.0)
        score = _clamp(bp_score * 0.35 + hr_score * 0.3 + hrv_score * 0.2 + activity_score * 0.15)
        factors = [
            ScoreFactor(
                name="blood_pressure",
                value=f"{int(round(systolic))}/{int(round(diastolic))}",
                impact=round(bp_score - 75.0, 3),
                direction="positive" if bp_score >= 75.0 else "negative",
                summary="Blood pressure remains near target." if bp_score >= 75.0 else "Blood pressure is reducing cardiovascular readiness.",
            ),
            ScoreFactor(
                name="resting_hr",
                value=round(resting_hr, 2),
                impact=round(hr_score - 72.0, 3),
                direction="positive" if hr_score >= 72.0 else "negative",
                summary="Resting heart rate supports cardiovascular recovery." if hr_score >= 72.0 else "Elevated resting heart rate reduced the cardiovascular score.",
            ),
            ScoreFactor(
                name="hrv",
                value=round(hrv, 2),
                impact=round(hrv_score - 70.0, 3),
                direction="positive" if hrv_score >= 70.0 else "negative",
                summary="HRV supports adaptation." if hrv_score >= 70.0 else "Lower HRV suggests elevated strain.",
            ),
        ]
        return round(score, 3), factors, {
            "systolic_bp": systolic,
            "diastolic_bp": diastolic,
            "resting_hr": resting_hr,
            "hrv": hrv,
            "activity_steps": steps,
        }
