from __future__ import annotations

from .._shared import clamp, circadian_wave


class HeartRateGenerator:
    @staticmethod
    def generate(*, profile: dict, hour: int, stress_index: float, fatigue_load: float, illness_burden: float, activity_steps: float, sleeping: bool) -> float:
        baseline = float(profile["baseline_metrics"]["resting_hr"])
        circadian = -4.5 if sleeping else circadian_wave(hour, 16, 3.0)
        exertion = min(activity_steps / 75.0, 32.0)
        value = baseline + circadian + (stress_index / 100.0) * 15.0 + fatigue_load * 8.0 + illness_burden * 12.0 + exertion
        return clamp(value, 38.0, 195.0)
