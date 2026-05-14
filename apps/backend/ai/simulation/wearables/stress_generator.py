from __future__ import annotations

from .._shared import clamp


class StressGenerator:
    @staticmethod
    def generate(*, profile: dict, stress_load: float, sleep_debt: float, illness_burden: float, activity_steps: float) -> float:
        baseline = float(profile["baseline_metrics"]["stress_index"])
        activity_relief = min(activity_steps / 1100.0, 1.0) * 7.0
        stress = baseline + stress_load * 28.0 + sleep_debt * 18.0 + illness_burden * 12.0 - activity_relief
        return clamp(stress, 0.0, 100.0)
