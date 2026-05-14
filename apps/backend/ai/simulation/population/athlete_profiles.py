from __future__ import annotations


def athlete_adjustments(profile_name: str, baselines: dict[str, float]) -> dict[str, float]:
    adjusted = dict(baselines)
    if profile_name == "athlete":
        adjusted["resting_hr"] -= 7.0
        adjusted["hrv"] += 16.0
        adjusted["activity_steps"] += 2800.0
        adjusted["recovery_index"] += 12.0
    if profile_name == "high_performance":
        adjusted["activity_steps"] += 1800.0
        adjusted["stress_index"] += 8.0
    return adjusted
