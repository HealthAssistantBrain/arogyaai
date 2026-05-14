from __future__ import annotations

from .._shared import clamp


class SpO2Generator:
    @staticmethod
    def generate(*, profile: dict, respiratory_load: float, illness_burden: float, sleeping: bool) -> float:
        baseline = float(profile["baseline_metrics"]["spo2"])
        sleep_penalty = 0.3 if sleeping else 0.0
        value = baseline - respiratory_load * 2.8 - illness_burden * 1.6 - sleep_penalty
        return clamp(value, 82.0, 100.0)
