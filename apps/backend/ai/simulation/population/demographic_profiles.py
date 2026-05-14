from __future__ import annotations

from typing import Any

from .._shared import build_rng

ARCHETYPES = [
    "athlete",
    "sedentary",
    "stressed_professional",
    "elderly",
    "diabetic",
    "hypertensive",
    "shift_worker",
    "high_performance",
    "chronic_fatigue",
]


def demographic_profile(profile_name: str, seed: int) -> dict[str, Any]:
    rng = build_rng(profile_name, seed, "demographic")
    age_map = {
        "athlete": rng.randint(21, 35),
        "sedentary": rng.randint(28, 52),
        "stressed_professional": rng.randint(29, 47),
        "elderly": rng.randint(64, 82),
        "diabetic": rng.randint(41, 68),
        "hypertensive": rng.randint(45, 72),
        "shift_worker": rng.randint(26, 49),
        "high_performance": rng.randint(25, 40),
        "chronic_fatigue": rng.randint(26, 55),
    }
    return {
        "synthetic_profile": profile_name,
        "demographic_profile": f"{profile_name}_demo",
        "age": age_map[profile_name],
        "sex": rng.choice(["female", "male"]),
        "timezone": "Asia/Calcutta",
    }
