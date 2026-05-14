from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .._shared import PHYSIOLOGICAL_LIMITS, bounded_normal, build_rng, clamp, log_simulation
from ..anomalies.anomaly_injector import AnomalyInjector
from ..anomalies.wearable_noise_engine import WearableNoiseEngine
from ..behavior.adherence_behavior import AdherenceBehavior
from ..behavior.exercise_behavior import ExerciseBehavior
from ..behavior.sleep_behavior import SleepBehavior
from ..behavior.stress_behavior import StressBehavior
from ..disease.cardiovascular_risk_progression import CardiovascularRiskProgression
from ..disease.diabetes_progression import DiabetesProgression
from ..disease.fatigue_progression import FatigueProgression
from ..disease.hypertension_progression import HypertensionProgression
from ..disease.respiratory_decline import RespiratoryDecline
from ..labs.blood_pressure_generator import BloodPressureGenerator
from ..labs.cholesterol_generator import CholesterolGenerator
from ..labs.glucose_generator import GlucoseGenerator
from ..labs.metabolic_panel_generator import MetabolicPanelGenerator
from ..recovery.burnout_recovery import BurnoutRecovery
from ..recovery.illness_recovery import IllnessRecovery
from ..recovery.recovery_engine import RecoveryEngine
from ..wearables.activity_generator import ActivityGenerator
from ..wearables.heart_rate_generator import HeartRateGenerator
from ..wearables.hrv_generator import HRVGenerator
from ..wearables.sleep_generator import SleepGenerator
from ..wearables.spo2_generator import SpO2Generator
from ..wearables.stress_generator import StressGenerator


class PhysiologyOrchestrator:
    @staticmethod
    def _noise(metric: str, value: float, rng_key: str) -> float:
        minimum, maximum = PHYSIOLOGICAL_LIMITS[metric]
        rng = build_rng(rng_key, metric)
        noise_draw = rng.uniform(-1.0, 1.0)
        return WearableNoiseEngine.apply(metric, value, noise_draw, minimum, maximum)

    @staticmethod
    def _daily_rollup(points: list[dict[str, Any]]) -> dict[str, Any]:
        if not points:
            return {}
        segment = points[-24:]
        return {
            "sleep_hours": max(item.get("sleep_hours", 0.0) for item in segment),
            "avg_heart_rate": sum(item.get("heart_rate", 0.0) or 0.0 for item in segment) / max(len(segment), 1),
            "avg_hrv": sum(item.get("hrv", 0.0) or 0.0 for item in segment) / max(len(segment), 1),
            "avg_stress": sum(item.get("stress_index", 0.0) or 0.0 for item in segment) / max(len(segment), 1),
            "avg_recovery": sum(item.get("recovery_index", 0.0) or 0.0 for item in segment) / max(len(segment), 1),
        }

    @classmethod
    def generate_sequence(
        cls,
        *,
        profile: dict,
        start_at: datetime,
        hours: int,
        event_schedule: dict[str, list[dict[str, Any]]],
        inject_anomalies: bool = True,
    ) -> list[dict[str, Any]]:
        state = {
            "sleep_debt": max(0.0, 7.2 - float(profile["baseline_metrics"]["sleep_hours"])) / 2.0,
            "metabolic_load": max(0.0, float(profile["baseline_metrics"]["glucose"]) - 92.0) / 60.0,
            "bp_load": max(0.0, float(profile["baseline_metrics"]["blood_pressure_systolic"]) - 120.0) / 40.0,
            "cardio_load": float(profile["disease_risks"]["cardiovascular"]) * 0.28,
            "respiratory_load": float(profile["disease_risks"]["respiratory"]) * 0.18,
            "fatigue_load": float(profile["disease_risks"]["fatigue"]) * 0.2,
            "recovery_balance": float(profile["baseline_metrics"]["recovery_index"]) / 100.0,
            "illness_burden": 0.0,
            "burnout_load": 0.0,
        }
        points: list[dict[str, Any]] = []
        actual_sleep_hours = float(profile["baseline_metrics"]["sleep_hours"])
        rng_key = f"{profile['user_id']}|{start_at.isoformat()}|{hours}"

        for step in range(hours):
            timestamp = start_at + timedelta(hours=step)
            date_key = timestamp.date().isoformat()
            hour = timestamp.hour
            workday = timestamp.weekday() < 5
            day_events = event_schedule.get(date_key, [])
            active_events = [event for event in day_events if abs(int(event["hour"]) - hour) <= 1]
            event_by_type = {event["type"]: float(event["intensity"]) for event in active_events}
            exercise_drive = ExerciseBehavior.hourly_propensity(profile, hour, event_by_type.get("exercise", 0.0))
            stress_load = StressBehavior.hourly_load(profile, hour, workday, event_by_type.get("work_stress", 0.0) + event_by_type.get("burnout", 0.0))
            sleep_target = SleepBehavior.nightly_target_hours(profile, state["sleep_debt"], stress_load)
            adherence = AdherenceBehavior.daily_adherence(profile, state["burnout_load"], event_by_type.get("intervention", 0.0))
            sleeping = (hour + int(profile.get("circadian_shift_hours", 0))) % 24 in {22, 23, 0, 1, 2, 3, 4, 5}

            if hour == 0:
                HypertensionProgression.apply(state, profile, stress_load, exercise_drive, adherence)
                DiabetesProgression.apply(state, profile, state["sleep_debt"], stress_load, adherence, exercise_drive)
                FatigueProgression.apply(state, profile, state["sleep_debt"], stress_load, state["illness_burden"])
                CardiovascularRiskProgression.apply(state, profile, state["bp_load"], stress_load, exercise_drive, state["sleep_debt"])
                RespiratoryDecline.apply(state, profile, state["illness_burden"], stress_load)
                RecoveryEngine.apply(state, profile, sleep_target, adherence, exercise_drive)
                IllnessRecovery.apply(state, adherence)
                BurnoutRecovery.apply(state, adherence, sleep_target)
                state["burnout_load"] = clamp(state["burnout_load"] + event_by_type.get("burnout", 0.0) * 0.06, 0.0, 1.0)
                state["illness_burden"] = clamp(state["illness_burden"] + event_by_type.get("illness", 0.0) * 0.12, 0.0, 1.0)

            activity_steps = ActivityGenerator.generate(
                profile=profile,
                hour=hour,
                sleeping=sleeping,
                exercise_drive=exercise_drive,
                fatigue_load=state["fatigue_load"],
            )
            stress_index = StressGenerator.generate(
                profile=profile,
                stress_load=stress_load,
                sleep_debt=state["sleep_debt"],
                illness_burden=state["illness_burden"],
                activity_steps=activity_steps,
            )
            heart_rate = HeartRateGenerator.generate(
                profile=profile,
                hour=hour,
                stress_index=stress_index,
                fatigue_load=state["fatigue_load"],
                illness_burden=state["illness_burden"],
                activity_steps=activity_steps,
                sleeping=sleeping,
            )
            hrv = HRVGenerator.generate(
                profile=profile,
                stress_index=stress_index,
                sleep_debt=state["sleep_debt"],
                recovery_balance=state["recovery_balance"],
                illness_burden=state["illness_burden"],
                activity_steps=activity_steps,
            )
            spo2 = SpO2Generator.generate(
                profile=profile,
                respiratory_load=state["respiratory_load"],
                illness_burden=state["illness_burden"],
                sleeping=sleeping,
            )
            glucose = GlucoseGenerator.generate(
                profile=profile,
                hour=hour,
                metabolic_load=state["metabolic_load"],
                stress_index=stress_index,
                activity_steps=activity_steps,
                sleeping=sleeping,
            )
            cholesterol = CholesterolGenerator.generate(profile=profile, metabolic_load=state["metabolic_load"], adherence=adherence)
            metabolic_panel = MetabolicPanelGenerator.generate(
                glucose=glucose,
                cholesterol=cholesterol,
                sleep_debt=state["sleep_debt"],
                stress_index=stress_index,
            )
            systolic_bp, diastolic_bp = BloodPressureGenerator.generate(
                profile=profile,
                hour=hour,
                bp_load=state["bp_load"],
                stress_index=stress_index,
                activity_steps=activity_steps,
                sleeping=sleeping,
            )

            if hour == 6:
                actual_sleep_hours = bounded_normal(build_rng(rng_key, date_key, "sleep"), sleep_target, 0.4, 4.0, 9.8)
                state["sleep_debt"] = clamp(state["sleep_debt"] * 0.55 + max(0.0, 7.2 - actual_sleep_hours) * 0.24, 0.0, 2.5)

            sleep_hours = SleepGenerator.generate(
                target_hours=sleep_target,
                actual_sleep_hours=actual_sleep_hours if hour == 6 else 0.0,
                sleep_debt=state["sleep_debt"],
                stress_index=stress_index,
            )
            recovery_index = clamp(
                float(profile["baseline_metrics"]["recovery_index"])
                + state["recovery_balance"] * 18.0
                - state["fatigue_load"] * 24.0
                - (stress_index / 100.0) * 12.0,
                0.0,
                100.0,
            )

            point = {
                "timestamp": timestamp,
                "heart_rate": cls._noise("heart_rate", heart_rate, f"{rng_key}|hr|{step}"),
                "hrv": cls._noise("hrv", hrv, f"{rng_key}|hrv|{step}"),
                "spo2": cls._noise("spo2", spo2, f"{rng_key}|spo2|{step}"),
                "activity_steps": cls._noise("activity_steps", activity_steps, f"{rng_key}|steps|{step}"),
                "stress_index": cls._noise("stress_index", stress_index, f"{rng_key}|stress|{step}"),
                "glucose": cls._noise("glucose", glucose, f"{rng_key}|glucose|{step}"),
                "cholesterol": cholesterol if hour == 7 else None,
                "metabolic_panel_score": metabolic_panel if hour == 7 else None,
                "blood_pressure_systolic": cls._noise("blood_pressure_systolic", systolic_bp, f"{rng_key}|bps|{step}"),
                "blood_pressure_diastolic": cls._noise("blood_pressure_diastolic", diastolic_bp, f"{rng_key}|bpd|{step}"),
                "sleep_hours": sleep_hours if hour == 6 else 0.0,
                "recovery_index": recovery_index,
                "sleeping": sleeping,
                "adherence": adherence,
                "trajectory_phase": "recovery" if recovery_index > 72 else "deterioration" if state["fatigue_load"] > 0.68 or state["bp_load"] > 0.72 else "stable",
                "anomaly_score": 0.0,
                "anomaly_labels": [],
                "state": {
                    "sleep_debt": round(state["sleep_debt"], 4),
                    "metabolic_load": round(state["metabolic_load"], 4),
                    "bp_load": round(state["bp_load"], 4),
                    "cardio_load": round(state["cardio_load"], 4),
                    "respiratory_load": round(state["respiratory_load"], 4),
                    "fatigue_load": round(state["fatigue_load"], 4),
                    "recovery_balance": round(state["recovery_balance"], 4),
                    "illness_burden": round(state["illness_burden"], 4),
                    "burnout_load": round(state["burnout_load"], 4),
                },
                "events": active_events,
            }
            points.append(point)

        if inject_anomalies:
            AnomalyInjector.inject(points, profile)

        log_simulation("TRAJECTORY GENERATED", user_id=profile["user_id"], points=len(points))
        return points
