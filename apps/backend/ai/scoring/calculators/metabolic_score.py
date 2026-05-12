from __future__ import annotations

from ..models.score_snapshot import ScoreFactor


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


class MetabolicScoreCalculator:
    @staticmethod
    def calculate(current: dict[str, float | None], labs: dict[str, float | None]) -> tuple[float, list[ScoreFactor], dict[str, float | None]]:
        glucose = float(labs.get("glucose") or current.get("glucose") or 95.0)
        hba1c = float(labs.get("hba1c") or 5.4)
        bmi = float(current.get("bmi") or 24.0)
        steps = float(current.get("activity_steps") or 7000.0)
        glucose_score = _clamp(100.0 - max(0.0, glucose - 95.0) * 1.1)
        hba1c_score = _clamp(100.0 - max(0.0, hba1c - 5.4) * 18.0)
        bmi_score = _clamp(100.0 - max(0.0, abs(bmi - 22.5) - 1.5) * 8.0)
        activity_score = _clamp((steps / 10000.0) * 100.0)
        score = _clamp(glucose_score * 0.35 + hba1c_score * 0.2 + bmi_score * 0.25 + activity_score * 0.2)
        factors = [
            ScoreFactor(
                name="glucose",
                value=round(glucose, 2),
                impact=round(glucose_score - 72.0, 3),
                direction="positive" if glucose <= 100.0 else "negative",
                summary="Glucose is in a healthy range." if glucose <= 100.0 else "Glucose is elevated relative to ideal metabolic control.",
            ),
            ScoreFactor(
                name="bmi",
                value=round(bmi, 2),
                impact=round(bmi_score - 72.0, 3),
                direction="positive" if bmi <= 25.0 else "negative",
                summary="Body composition supports metabolic health." if bmi <= 25.0 else "BMI is adding metabolic load.",
            ),
        ]
        return round(score, 3), factors, {"glucose": glucose, "hba1c": hba1c, "bmi": bmi, "activity_steps": steps}
