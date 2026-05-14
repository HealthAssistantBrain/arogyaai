from __future__ import annotations

from typing import Any

from .._shared import risk_level, slope


class DeteriorationForecaster:
    @staticmethod
    def forecast(points: list[dict[str, Any]]) -> dict[str, Any]:
        recent = points[-48:]
        hr_series = [float(point["heart_rate"] or 0.0) for point in recent]
        hrv_series = [float(point["hrv"] or 0.0) for point in recent]
        stress_series = [float(point["stress_index"] or 0.0) for point in recent]
        score = max(0.0, min(1.0, slope(hr_series) * 0.03 + (-slope(hrv_series)) * 0.02 + slope(stress_series) * 0.02))
        return {
            "risk_score": round(score, 4),
            "risk_level": risk_level(score),
            "drivers": ["heart_rate", "hrv", "stress_index"],
        }
