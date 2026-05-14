from __future__ import annotations

from typing import Any


def apply_age_adjustments(age: int, baselines: dict[str, float]) -> dict[str, Any]:
    adjusted = dict(baselines)
    age_factor = max(age - 40, 0) / 40.0
    adjusted["resting_hr"] += age_factor * 4.0
    adjusted["hrv"] -= age_factor * 12.0
    adjusted["spo2"] -= age_factor * 0.8
    adjusted["blood_pressure_systolic"] += age_factor * 10.0
    adjusted["blood_pressure_diastolic"] += age_factor * 5.0
    adjusted["recovery_index"] -= age_factor * 12.0
    adjusted["activity_steps"] -= age_factor * 1800.0
    return {"baselines": adjusted, "recovery_capacity": max(0.2, 0.75 - age_factor * 0.35)}
