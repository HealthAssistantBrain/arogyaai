from __future__ import annotations

from typing import Any

from .._shared import clamp, trend_direction


class RecoveryForecaster:
    @staticmethod
    def forecast(points: list[dict[str, Any]]) -> dict[str, Any]:
        recent = points[-48:]
        if not recent:
            return {"recovery_probability": 0.0, "direction": "stable"}
        start = recent[0]["recovery_index"]
        end = recent[-1]["recovery_index"]
        probability = clamp((end - 35.0) / 55.0, 0.0, 1.0)
        return {
            "recovery_probability": round(probability, 4),
            "direction": trend_direction((end - start) / 100.0),
        }
