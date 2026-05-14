from __future__ import annotations

from .._shared import clamp


class ActivityGenerator:
    @staticmethod
    def generate(*, profile: dict, hour: int, sleeping: bool, exercise_drive: float, fatigue_load: float) -> float:
        baseline = float(profile["baseline_metrics"]["activity_steps"]) / 16.0
        if sleeping:
            return 0.0
        day_factor = 1.2 if 7 <= hour <= 20 else 0.3
        steps = baseline * day_factor * (0.45 + exercise_drive * 1.1) * (1.0 - fatigue_load * 0.4)
        return clamp(steps, 0.0, 1600.0)
