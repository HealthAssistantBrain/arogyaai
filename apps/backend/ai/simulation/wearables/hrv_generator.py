from __future__ import annotations

from .._shared import clamp


class HRVGenerator:
    @staticmethod
    def generate(*, profile: dict, stress_index: float, sleep_debt: float, recovery_balance: float, illness_burden: float, activity_steps: float) -> float:
        baseline = float(profile["baseline_metrics"]["hrv"])
        exercise_boost = min(activity_steps / 900.0, 1.0) * 6.0
        value = baseline - (stress_index / 100.0) * 22.0 - sleep_debt * 14.0 - illness_burden * 8.0 + recovery_balance * 16.0 + exercise_boost
        return clamp(value, 10.0, 160.0)
