from __future__ import annotations

from typing import Any

from ..population.age_based_profiles import apply_age_adjustments
from ..population.athlete_profiles import athlete_adjustments
from ..population.demographic_profiles import ARCHETYPES, demographic_profile
from ..population.lifestyle_profiles import lifestyle_profile
from ..schemas.physiological_profile import PhysiologicalProfile


class SyntheticPopulation:
    BASELINES: dict[str, dict[str, float]] = {
        "athlete": {"resting_hr": 56, "hrv": 72, "spo2": 98.4, "sleep_hours": 7.9, "activity_steps": 11800, "stress_index": 28, "glucose": 89, "cholesterol": 166, "blood_pressure_systolic": 114, "blood_pressure_diastolic": 71, "recovery_index": 84},
        "sedentary": {"resting_hr": 72, "hrv": 43, "spo2": 97.2, "sleep_hours": 7.0, "activity_steps": 4300, "stress_index": 44, "glucose": 98, "cholesterol": 198, "blood_pressure_systolic": 126, "blood_pressure_diastolic": 81, "recovery_index": 56},
        "stressed_professional": {"resting_hr": 69, "hrv": 38, "spo2": 97.0, "sleep_hours": 6.2, "activity_steps": 6100, "stress_index": 66, "glucose": 101, "cholesterol": 202, "blood_pressure_systolic": 129, "blood_pressure_diastolic": 84, "recovery_index": 49},
        "elderly": {"resting_hr": 71, "hrv": 32, "spo2": 95.9, "sleep_hours": 7.2, "activity_steps": 3800, "stress_index": 41, "glucose": 103, "cholesterol": 191, "blood_pressure_systolic": 136, "blood_pressure_diastolic": 79, "recovery_index": 47},
        "diabetic": {"resting_hr": 73, "hrv": 35, "spo2": 96.8, "sleep_hours": 6.7, "activity_steps": 5000, "stress_index": 54, "glucose": 131, "cholesterol": 208, "blood_pressure_systolic": 132, "blood_pressure_diastolic": 83, "recovery_index": 45},
        "hypertensive": {"resting_hr": 74, "hrv": 37, "spo2": 97.0, "sleep_hours": 6.8, "activity_steps": 5200, "stress_index": 56, "glucose": 101, "cholesterol": 205, "blood_pressure_systolic": 144, "blood_pressure_diastolic": 90, "recovery_index": 46},
        "shift_worker": {"resting_hr": 71, "hrv": 36, "spo2": 96.8, "sleep_hours": 5.8, "activity_steps": 5900, "stress_index": 61, "glucose": 104, "cholesterol": 197, "blood_pressure_systolic": 128, "blood_pressure_diastolic": 82, "recovery_index": 44},
        "high_performance": {"resting_hr": 61, "hrv": 58, "spo2": 98.1, "sleep_hours": 6.7, "activity_steps": 9700, "stress_index": 58, "glucose": 92, "cholesterol": 178, "blood_pressure_systolic": 121, "blood_pressure_diastolic": 76, "recovery_index": 67},
        "chronic_fatigue": {"resting_hr": 76, "hrv": 28, "spo2": 96.5, "sleep_hours": 6.5, "activity_steps": 3900, "stress_index": 59, "glucose": 100, "cholesterol": 193, "blood_pressure_systolic": 127, "blood_pressure_diastolic": 81, "recovery_index": 35},
    }

    DISEASE_WEIGHTS: dict[str, dict[str, float]] = {
        "athlete": {"hypertension": 0.12, "diabetes": 0.08, "fatigue": 0.14, "cardiovascular": 0.12, "respiratory": 0.1},
        "sedentary": {"hypertension": 0.38, "diabetes": 0.34, "fatigue": 0.26, "cardiovascular": 0.35, "respiratory": 0.18},
        "stressed_professional": {"hypertension": 0.44, "diabetes": 0.26, "fatigue": 0.48, "cardiovascular": 0.39, "respiratory": 0.18},
        "elderly": {"hypertension": 0.52, "diabetes": 0.31, "fatigue": 0.34, "cardiovascular": 0.51, "respiratory": 0.27},
        "diabetic": {"hypertension": 0.42, "diabetes": 0.75, "fatigue": 0.32, "cardiovascular": 0.47, "respiratory": 0.19},
        "hypertensive": {"hypertension": 0.82, "diabetes": 0.27, "fatigue": 0.28, "cardiovascular": 0.63, "respiratory": 0.17},
        "shift_worker": {"hypertension": 0.33, "diabetes": 0.29, "fatigue": 0.52, "cardiovascular": 0.31, "respiratory": 0.16},
        "high_performance": {"hypertension": 0.24, "diabetes": 0.14, "fatigue": 0.37, "cardiovascular": 0.22, "respiratory": 0.11},
        "chronic_fatigue": {"hypertension": 0.25, "diabetes": 0.19, "fatigue": 0.88, "cardiovascular": 0.28, "respiratory": 0.16},
    }

    @classmethod
    def build_profile(cls, *, profile_name: str, user_id: str, seed: int) -> PhysiologicalProfile:
        demographic = demographic_profile(profile_name, seed)
        lifestyle = lifestyle_profile(profile_name)
        baselines = athlete_adjustments(profile_name, cls.BASELINES[profile_name])
        age_adjusted = apply_age_adjustments(demographic["age"], baselines)

        chronotype = "late" if profile_name in {"shift_worker", "stressed_professional"} else "balanced"
        conditions = {
            "diabetic": ["type_2_diabetes"],
            "hypertensive": ["hypertension"],
            "chronic_fatigue": ["chronic_fatigue"],
            "elderly": ["age_related_recovery_risk"],
        }.get(profile_name, [])

        return PhysiologicalProfile(
            user_id=user_id,
            synthetic_profile=profile_name,
            demographic_profile=demographic["demographic_profile"],
            age=demographic["age"],
            sex=demographic["sex"],
            chronotype=chronotype,
            timezone=demographic["timezone"],
            baseline_metrics=age_adjusted["baselines"],
            lifestyle_factors=lifestyle,
            behavior_traits={
                "exercise_habit": float(lifestyle["exercise_habit"]),
                "sleep_discipline": float(lifestyle["sleep_discipline"]),
                "adherence": float(lifestyle["adherence"]),
                "diet_quality": float(lifestyle["diet_quality"]),
            },
            disease_risks=cls.DISEASE_WEIGHTS[profile_name],
            resilience=max(0.2, min(0.95, 0.55 + float(lifestyle["exercise_habit"]) * 0.18)),
            recovery_capacity=float(age_adjusted["recovery_capacity"]),
            circadian_shift_hours=8 if profile_name == "shift_worker" else 0,
            chronic_conditions=conditions,
            tags=[profile_name, chronotype],
            metadata={"seed": seed},
        )

    @classmethod
    def build_population(cls, size: int, seed: int) -> list[PhysiologicalProfile]:
        profiles: list[PhysiologicalProfile] = []
        for index in range(size):
            profile_name = ARCHETYPES[index % len(ARCHETYPES)]
            profiles.append(cls.build_profile(profile_name=profile_name, user_id=f"synthetic-user-{index+1:04d}", seed=seed + index))
        return profiles
