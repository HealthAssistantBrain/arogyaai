from __future__ import annotations

from .._shared import clamp


class GlucoseGenerator:
    @staticmethod
    def generate(*, profile: dict, hour: int, metabolic_load: float, stress_index: float, activity_steps: float, sleeping: bool) -> float:
        baseline = float(profile["baseline_metrics"]["glucose"])
        meal_spike = 18.0 if hour in {8, 13, 20} and not sleeping else 0.0
        activity_relief = min(activity_steps / 850.0, 1.0) * 9.0
        value = baseline + metabolic_load * 34.0 + (stress_index / 100.0) * 16.0 + meal_spike - activity_relief
        return clamp(value, 60.0, 290.0)
