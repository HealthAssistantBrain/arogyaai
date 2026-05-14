from __future__ import annotations

from .._shared import clamp


class CholesterolGenerator:
    @staticmethod
    def generate(*, profile: dict, metabolic_load: float, adherence: float) -> float:
        baseline = float(profile["baseline_metrics"]["cholesterol"])
        value = baseline + metabolic_load * 26.0 - adherence * 9.0
        return clamp(value, 100.0, 340.0)
