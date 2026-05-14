from __future__ import annotations

from .._shared import circadian_wave


class ExerciseBehavior:
    @staticmethod
    def hourly_propensity(profile: dict, hour: int, event_intensity: float) -> float:
        base = float(profile["behavior_traits"]["exercise_habit"])
        peak = 18 if profile["synthetic_profile"] != "athlete" else 7
        circadian = max(0.0, circadian_wave(hour, peak, 0.5) + 0.35)
        return max(0.0, min(1.0, base * circadian + event_intensity * 0.3))
