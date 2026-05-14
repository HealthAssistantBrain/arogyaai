from __future__ import annotations

from .._shared import circadian_wave


class StressBehavior:
    @staticmethod
    def hourly_load(profile: dict, hour: int, workday: bool, event_intensity: float) -> float:
        base = float(profile["baseline_metrics"]["stress_index"]) / 100.0
        work_peak = 15 + int(profile.get("circadian_shift_hours", 0))
        work_pressure = max(0.0, circadian_wave(hour, work_peak, 0.55) + 0.45) if workday else 0.15
        return max(0.0, min(1.0, base * 0.45 + work_pressure * 0.45 + event_intensity * 0.35))
