from __future__ import annotations

from .._shared import clamp


class SleepGenerator:
    @staticmethod
    def generate(*, target_hours: float, actual_sleep_hours: float, sleep_debt: float, stress_index: float) -> float:
        value = actual_sleep_hours - sleep_debt * 0.2 - (stress_index / 100.0) * 0.45 + max(0.0, target_hours - 7.0) * 0.2
        return clamp(value, 0.0, 12.0)
