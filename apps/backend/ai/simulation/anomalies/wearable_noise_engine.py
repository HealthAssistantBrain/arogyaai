from __future__ import annotations

from .._shared import clamp


class WearableNoiseEngine:
    NOISE = {
        "heart_rate": 1.8,
        "hrv": 2.5,
        "spo2": 0.35,
        "activity_steps": 22.0,
        "stress_index": 1.5,
        "glucose": 2.0,
        "blood_pressure_systolic": 1.6,
        "blood_pressure_diastolic": 1.2,
    }

    @classmethod
    def apply(cls, metric: str, value: float, noise_draw: float, minimum: float, maximum: float) -> float:
        spread = cls.NOISE.get(metric, 0.0)
        return clamp(value + noise_draw * spread, minimum, maximum)
