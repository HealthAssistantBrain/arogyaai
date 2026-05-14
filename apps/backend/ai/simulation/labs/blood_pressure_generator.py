from __future__ import annotations

from .._shared import clamp, circadian_wave


class BloodPressureGenerator:
    @staticmethod
    def generate(*, profile: dict, hour: int, bp_load: float, stress_index: float, activity_steps: float, sleeping: bool) -> tuple[float, float]:
        sys_base = float(profile["baseline_metrics"]["blood_pressure_systolic"])
        dia_base = float(profile["baseline_metrics"]["blood_pressure_diastolic"])
        circadian = -6.0 if sleeping else circadian_wave(hour, 14, 5.0)
        exertion = min(activity_steps / 120.0, 10.0)
        systolic = sys_base + bp_load * 18.0 + (stress_index / 100.0) * 10.0 + circadian + exertion
        diastolic = dia_base + bp_load * 12.0 + (stress_index / 100.0) * 6.0 + circadian * 0.4 + exertion * 0.35
        return clamp(systolic, 85.0, 215.0), clamp(diastolic, 48.0, 135.0)
