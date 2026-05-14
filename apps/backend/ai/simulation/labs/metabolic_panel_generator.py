from __future__ import annotations

from .._shared import clamp


class MetabolicPanelGenerator:
    @staticmethod
    def generate(*, glucose: float, cholesterol: float, sleep_debt: float, stress_index: float) -> float:
        score = 100.0 - ((glucose - 85.0) * 0.32 + (cholesterol - 165.0) * 0.08 + sleep_debt * 9.0 + (stress_index / 100.0) * 12.0)
        return clamp(score, 0.0, 100.0)
