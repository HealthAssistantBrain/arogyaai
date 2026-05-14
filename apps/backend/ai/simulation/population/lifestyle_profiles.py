from __future__ import annotations

from typing import Any


def lifestyle_profile(profile_name: str) -> dict[str, Any]:
    profiles: dict[str, dict[str, Any]] = {
        "athlete": {"exercise_habit": 0.92, "sleep_discipline": 0.82, "adherence": 0.76, "diet_quality": 0.78},
        "sedentary": {"exercise_habit": 0.28, "sleep_discipline": 0.55, "adherence": 0.58, "diet_quality": 0.52},
        "stressed_professional": {"exercise_habit": 0.42, "sleep_discipline": 0.38, "adherence": 0.57, "diet_quality": 0.5},
        "elderly": {"exercise_habit": 0.45, "sleep_discipline": 0.7, "adherence": 0.84, "diet_quality": 0.68},
        "diabetic": {"exercise_habit": 0.46, "sleep_discipline": 0.56, "adherence": 0.71, "diet_quality": 0.63},
        "hypertensive": {"exercise_habit": 0.4, "sleep_discipline": 0.54, "adherence": 0.72, "diet_quality": 0.58},
        "shift_worker": {"exercise_habit": 0.38, "sleep_discipline": 0.25, "adherence": 0.6, "diet_quality": 0.48},
        "high_performance": {"exercise_habit": 0.74, "sleep_discipline": 0.5, "adherence": 0.62, "diet_quality": 0.66},
        "chronic_fatigue": {"exercise_habit": 0.22, "sleep_discipline": 0.44, "adherence": 0.54, "diet_quality": 0.57},
    }
    return profiles[profile_name]
