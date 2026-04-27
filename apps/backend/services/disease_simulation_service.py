from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from models import MedicalHistory, User, UserProfile, UserVital, UserVitalTypeEnum, VitalsData


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_float(value, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _age_from_dob(dob) -> int | None:
    if not dob:
        return None
    today = _utc_now().date()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return max(years, 0)


def _avg(items: Iterable[float]) -> float | None:
    values = [float(item) for item in items if item is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _normalize_focus(value: str | None) -> str:
    text = (value or "cardiovascular").strip().lower()
    aliases = {
        "heart": "cardiovascular",
        "heart disease": "cardiovascular",
        "cardio": "cardiovascular",
        "cardiovascular": "cardiovascular",
        "diabetes": "diabetes",
        "sugar": "diabetes",
        "type 2 diabetes": "diabetes",
        "respiratory": "respiratory",
        "lungs": "respiratory",
        "asthma": "respiratory",
    }
    return aliases.get(text, text)


@dataclass
class MetricBundle:
    sleep_hours: float
    daily_steps: int
    weight_kg: float
    stress_level: int
    weekly_exercise_hours: float
    heart_rate_bpm: int
    systolic_bp: int
    diastolic_bp: int
    spo2: float
    fasting_glucose: float

    def as_dict(self) -> dict:
        return {
            "sleep_hours": round(self.sleep_hours, 1),
            "daily_steps": int(self.daily_steps),
            "weight_kg": round(self.weight_kg, 1),
            "stress_level": int(self.stress_level),
            "weekly_exercise_hours": round(self.weekly_exercise_hours, 1),
            "heart_rate_bpm": int(self.heart_rate_bpm),
            "systolic_bp": int(self.systolic_bp),
            "diastolic_bp": int(self.diastolic_bp),
            "spo2": round(self.spo2, 1),
            "fasting_glucose": round(self.fasting_glucose, 1),
        }


class DiseaseSimulationService:
    @staticmethod
    def _latest_profile(db: Session, user: User) -> UserProfile | None:
        return db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

    @staticmethod
    def _latest_vitals(db: Session, user: User) -> VitalsData | None:
        return (
            db.query(VitalsData)
            .filter(VitalsData.user_id == user.id)
            .order_by(VitalsData.recorded_at.desc())
            .first()
        )

    @staticmethod
    def _recent_user_vitals(db: Session, user: User, vital_type: UserVitalTypeEnum, days: int = 7) -> list[UserVital]:
        return (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.vital_type == vital_type,
                UserVital.timestamp >= _utc_now() - timedelta(days=days),
            )
            .order_by(UserVital.timestamp.desc())
            .all()
        )

    @staticmethod
    def _conditions(db: Session, user: User) -> list[str]:
        rows = (
            db.query(MedicalHistory)
            .filter(MedicalHistory.user_id == user.id, MedicalHistory.is_deleted == False)  # noqa: E712
            .order_by(MedicalHistory.created_at.desc())
            .all()
        )
        return [row.condition_name.strip() for row in rows if row.condition_name]

    @staticmethod
    def _estimated_exercise_hours(steps: int) -> float:
        return _clamp((steps / 10000) * 4.5, 0.0, 10.0)

    @staticmethod
    def build_baseline(db: Session, user: User) -> dict:
        profile = DiseaseSimulationService._latest_profile(db, user)
        latest_vitals = DiseaseSimulationService._latest_vitals(db, user)
        sleep_records = DiseaseSimulationService._recent_user_vitals(db, user, UserVitalTypeEnum.SLEEP, days=7)
        steps_records = DiseaseSimulationService._recent_user_vitals(db, user, UserVitalTypeEnum.STEPS, days=7)
        heart_records = DiseaseSimulationService._recent_user_vitals(db, user, UserVitalTypeEnum.HEART_RATE, days=3)
        conditions = DiseaseSimulationService._conditions(db, user)

        age = _age_from_dob(profile.date_of_birth) if profile else None
        if age is None and profile is not None:
            age = _safe_int(getattr(profile, "age", None))
        weight_kg = _safe_float(getattr(profile, "weight_kg", None), 72.0) or 72.0
        height_cm = _safe_float(getattr(profile, "height_cm", None), 170.0) or 170.0
        bmi = round(weight_kg / ((height_cm / 100) ** 2), 1) if height_cm > 0 else None

        avg_sleep = _avg([record.value for record in sleep_records]) or 7.0
        avg_steps = _safe_int(_avg([record.value for record in steps_records]), 7000) or 7000
        avg_heart_rate = _safe_int(_avg([record.value for record in heart_records]), None)

        baseline = MetricBundle(
            sleep_hours=round(avg_sleep, 1),
            daily_steps=avg_steps,
            weight_kg=round(weight_kg, 1),
            stress_level=5,
            weekly_exercise_hours=round(DiseaseSimulationService._estimated_exercise_hours(avg_steps), 1),
            heart_rate_bpm=_safe_int(getattr(latest_vitals, "heart_rate_bpm", None), avg_heart_rate or 78) or 78,
            systolic_bp=_safe_int(getattr(latest_vitals, "blood_pressure_sys", None), 128) or 128,
            diastolic_bp=_safe_int(getattr(latest_vitals, "blood_pressure_dia", None), 82) or 82,
            spo2=_safe_float(getattr(latest_vitals, "oxygen_saturation_spo2", None), 97.0) or 97.0,
            fasting_glucose=95.0,
        )

        known_focuses = ["cardiovascular", "diabetes", "respiratory"]
        condition_hints = []
        lowered_conditions = [item.lower() for item in conditions]
        if any(keyword in " ".join(lowered_conditions) for keyword in ("heart", "cardio", "hypertension", "bp")):
            condition_hints.append("cardiovascular")
        if any(keyword in " ".join(lowered_conditions) for keyword in ("diabetes", "sugar", "glucose")):
            condition_hints.append("diabetes")
        if any(keyword in " ".join(lowered_conditions) for keyword in ("asthma", "copd", "lung", "respiratory")):
            condition_hints.append("respiratory")

        focus_options = list(dict.fromkeys(condition_hints + known_focuses))

        return {
            "baseline": baseline,
            "profile": {
                "age": age,
                "height_cm": round(height_cm, 1),
                "weight_kg": round(weight_kg, 1),
                "bmi": bmi,
            },
            "conditions": conditions,
            "focus_options": focus_options,
            "assumptions": [
                "Stress level defaults to 5/10 because no stress history is stored yet.",
                "Fasting glucose defaults to 95 mg/dL unless you later connect lab values.",
                "Weekly exercise hours are estimated from recent step count when explicit exercise logs are unavailable.",
            ],
        }

    @staticmethod
    def _build_metrics(baseline: MetricBundle, simulation: dict | None) -> MetricBundle:
        overrides = simulation or {}
        return MetricBundle(
            sleep_hours=_clamp(_safe_float(overrides.get("sleep_hours"), baseline.sleep_hours) or baseline.sleep_hours, 3.0, 12.0),
            daily_steps=_safe_int(overrides.get("daily_steps"), baseline.daily_steps) or baseline.daily_steps,
            weight_kg=_clamp(_safe_float(overrides.get("weight_kg"), baseline.weight_kg) or baseline.weight_kg, 30.0, 250.0),
            stress_level=_clamp(float(_safe_int(overrides.get("stress_level"), baseline.stress_level) or baseline.stress_level), 1.0, 10.0),
            weekly_exercise_hours=_clamp(_safe_float(overrides.get("weekly_exercise_hours"), baseline.weekly_exercise_hours) or baseline.weekly_exercise_hours, 0.0, 20.0),
            heart_rate_bpm=_safe_int(overrides.get("heart_rate_bpm"), baseline.heart_rate_bpm) or baseline.heart_rate_bpm,
            systolic_bp=_safe_int(overrides.get("systolic_bp"), baseline.systolic_bp) or baseline.systolic_bp,
            diastolic_bp=_safe_int(overrides.get("diastolic_bp"), baseline.diastolic_bp) or baseline.diastolic_bp,
            spo2=_clamp(_safe_float(overrides.get("spo2"), baseline.spo2) or baseline.spo2, 80.0, 100.0),
            fasting_glucose=_clamp(_safe_float(overrides.get("fasting_glucose"), baseline.fasting_glucose) or baseline.fasting_glucose, 60.0, 300.0),
        )

    @staticmethod
    def _risk_label(score: float) -> str:
        if score >= 75:
            return "Critical"
        if score >= 55:
            return "High"
        if score >= 30:
            return "Moderate"
        return "Low"

    @staticmethod
    def _condition_bonus(conditions: list[str], keywords: tuple[str, ...], bonus: float) -> float:
        text = " ".join(item.lower() for item in conditions)
        return bonus if any(keyword in text for keyword in keywords) else 0.0

    @staticmethod
    def _domain_scores(metrics: MetricBundle, profile: dict, conditions: list[str]) -> dict[str, float]:
        age = profile.get("age") or 35
        bmi = profile.get("bmi") or 24.0
        cardio = 8.0
        cardio += max(0, age - 35) * 0.45
        cardio += max(0.0, bmi - 24.0) * 1.8
        cardio += abs(metrics.heart_rate_bpm - 72) * 0.42
        cardio += max(0, metrics.systolic_bp - 120) * 0.38
        cardio += max(0, metrics.diastolic_bp - 80) * 0.28
        cardio += max(0.0, 7.0 - metrics.sleep_hours) * 3.0
        cardio += max(0, 8000 - metrics.daily_steps) / 400
        cardio += max(0, metrics.stress_level - 4) * 3.4
        cardio += max(0.0, 3.0 - metrics.weekly_exercise_hours) * 3.5
        cardio += DiseaseSimulationService._condition_bonus(conditions, ("heart", "cardio", "hypertension", "stent"), 14.0)

        diabetes = 6.0
        diabetes += max(0.0, bmi - 23.5) * 2.2
        diabetes += max(0.0, metrics.fasting_glucose - 95.0) * 0.45
        diabetes += max(0, 7500 - metrics.daily_steps) / 450
        diabetes += max(0.0, 7.0 - metrics.sleep_hours) * 2.8
        diabetes += max(0.0, 2.5 - metrics.weekly_exercise_hours) * 4.0
        diabetes += max(0, metrics.stress_level - 4) * 2.3
        diabetes += DiseaseSimulationService._condition_bonus(conditions, ("diabetes", "glucose", "insulin"), 16.0)

        respiratory = 5.0
        respiratory += max(0.0, 96.0 - metrics.spo2) * 7.0
        respiratory += max(0, metrics.heart_rate_bpm - 82) * 0.5
        respiratory += max(0.0, 6.5 - metrics.sleep_hours) * 2.0
        respiratory += max(0, 6500 - metrics.daily_steps) / 650
        respiratory += max(0, metrics.stress_level - 5) * 1.8
        respiratory += DiseaseSimulationService._condition_bonus(conditions, ("asthma", "copd", "respiratory", "lung"), 18.0)

        return {
            "cardiovascular": round(_clamp(cardio, 2.0, 95.0), 1),
            "diabetes": round(_clamp(diabetes, 2.0, 95.0), 1),
            "respiratory": round(_clamp(respiratory, 1.0, 95.0), 1),
        }

    @staticmethod
    def _focus_targets(focus: str) -> dict:
        targets = {
            "cardiovascular": {
                "heart_rate_bpm": (60, 80),
                "systolic_bp": (100, 120),
                "diastolic_bp": (65, 80),
                "sleep_hours": (7, 8.5),
                "daily_steps": (8000, 12000),
                "stress_level": (1, 4),
                "weekly_exercise_hours": (3, 6),
            },
            "diabetes": {
                "fasting_glucose": (80, 99),
                "weight_kg": None,
                "sleep_hours": (7, 8.5),
                "daily_steps": (8500, 12000),
                "stress_level": (1, 4),
                "weekly_exercise_hours": (3, 7),
            },
            "respiratory": {
                "spo2": (96, 100),
                "heart_rate_bpm": (60, 82),
                "sleep_hours": (7, 8.5),
                "daily_steps": (7000, 11000),
                "stress_level": (1, 5),
            },
        }
        return targets.get(focus, targets["cardiovascular"])

    @staticmethod
    def _normalization_summary(focus: str, before: float, after: float, conditions: list[str], timeframe_months: int) -> dict:
        chronic_bonus = DiseaseSimulationService._condition_bonus(conditions, tuple(focus.split()), 1.0)
        can_normalize = after < 20 and chronic_bonus == 0
        if can_normalize:
            headline = f"If you maintain this plan for {timeframe_months} months, your {focus} profile can move close to the low-risk range."
        elif after < before:
            headline = f"Risk improves meaningfully in {timeframe_months} months, but an existing condition still leaves residual {focus} risk."
        else:
            headline = f"This scenario is unlikely to normalize your {focus} risk within {timeframe_months} months."

        improvement = round(before - after, 1)
        likelihood = "High" if can_normalize else "Moderate" if improvement >= 10 else "Low"
        return {
            "can_return_to_normal": can_normalize,
            "likelihood": likelihood,
            "headline": headline,
            "risk_reduction_points": improvement,
        }

    @staticmethod
    def _key_drivers(focus: str, before_metrics: MetricBundle, after_metrics: MetricBundle, before_scores: dict, after_scores: dict) -> list[str]:
        drivers = []
        if after_metrics.heart_rate_bpm > before_metrics.heart_rate_bpm and focus == "cardiovascular":
            drivers.append("Heart rate increase pushes cardiovascular strain upward, especially when a prior heart condition already exists.")
        if after_metrics.systolic_bp > before_metrics.systolic_bp:
            drivers.append("Higher blood pressure keeps vascular risk elevated even if other habits improve.")
        if after_metrics.daily_steps > before_metrics.daily_steps:
            drivers.append("More daily movement improves insulin sensitivity and long-term heart resilience.")
        if after_metrics.sleep_hours > before_metrics.sleep_hours:
            drivers.append("Better sleep supports recovery, lowers sympathetic drive, and improves overall risk recovery.")
        if after_metrics.stress_level < before_metrics.stress_level:
            drivers.append("Lower stress reduces sustained hormonal load, which helps both heart and metabolic control.")
        if after_scores[focus] >= before_scores[focus]:
            drivers.append("The chosen changes are not strong enough to offset your existing baseline risk.")
        return drivers[:4]

    @staticmethod
    def simulate(db: Session, user: User, payload) -> dict:
        baseline_context = DiseaseSimulationService.build_baseline(db, user)
        baseline_metrics: MetricBundle = baseline_context["baseline"]
        profile = baseline_context["profile"]
        conditions = baseline_context["conditions"]

        focus = _normalize_focus(getattr(payload, "focus_condition", None))
        timeframe_months = max(1, min(int(getattr(payload, "timeframe_months", 6) or 6), 12))
        simulation_metrics = DiseaseSimulationService._build_metrics(
            baseline_metrics,
            getattr(getattr(payload, "simulation", None), "model_dump", lambda: {})(),
        )

        current_scores = DiseaseSimulationService._domain_scores(baseline_metrics, profile, conditions)
        simulated_scores = DiseaseSimulationService._domain_scores(simulation_metrics, profile, conditions)

        risks = [
            {
                "key": "cardiovascular",
                "label": "Cardiovascular",
                "current_risk": current_scores["cardiovascular"],
                "simulated_risk": simulated_scores["cardiovascular"],
                "delta": round(simulated_scores["cardiovascular"] - current_scores["cardiovascular"], 1),
                "risk_level": DiseaseSimulationService._risk_label(simulated_scores["cardiovascular"]),
            },
            {
                "key": "diabetes",
                "label": "Diabetes (Type II)",
                "current_risk": current_scores["diabetes"],
                "simulated_risk": simulated_scores["diabetes"],
                "delta": round(simulated_scores["diabetes"] - current_scores["diabetes"], 1),
                "risk_level": DiseaseSimulationService._risk_label(simulated_scores["diabetes"]),
            },
            {
                "key": "respiratory",
                "label": "Respiratory",
                "current_risk": current_scores["respiratory"],
                "simulated_risk": simulated_scores["respiratory"],
                "delta": round(simulated_scores["respiratory"] - current_scores["respiratory"], 1),
                "risk_level": DiseaseSimulationService._risk_label(simulated_scores["respiratory"]),
            },
        ]

        before_focus = current_scores.get(focus, current_scores["cardiovascular"])
        after_focus = simulated_scores.get(focus, simulated_scores["cardiovascular"])
        normalization = DiseaseSimulationService._normalization_summary(
            focus,
            before_focus,
            after_focus,
            conditions,
            timeframe_months,
        )
        targets = DiseaseSimulationService._focus_targets(focus)

        recommendations = []
        for metric_name, target_range in targets.items():
            if target_range is None:
                continue
            current_value = getattr(simulation_metrics, metric_name)
            low, high = target_range
            if current_value < low:
                recommendations.append(f"Increase {metric_name.replace('_', ' ')} toward {low}-{high}.")
            elif current_value > high:
                recommendations.append(f"Reduce {metric_name.replace('_', ' ')} toward {low}-{high}.")
        if not recommendations:
            recommendations.append("Current simulation is already close to the desired target range. Maintain it consistently.")

        focus_title = focus.replace("_", " ").title()
        simulation_summary = (
            f"For {focus_title}, your estimated risk moves from {before_focus:.1f}% to {after_focus:.1f}% over "
            f"{timeframe_months} months under this scenario."
        )
        if focus == "cardiovascular":
            simulation_summary += (
                f" Heart rate at {simulation_metrics.heart_rate_bpm} bpm and blood pressure at "
                f"{simulation_metrics.systolic_bp}/{simulation_metrics.diastolic_bp} are the strongest heart-specific drivers."
            )

        return {
            "success": True,
            "status": "ready",
            "source": "rule_engine",
            "error": None,
            "data": {
                "focus_condition": focus,
                "timeframe_months": timeframe_months,
                "baseline": baseline_metrics.as_dict(),
                "simulation": simulation_metrics.as_dict(),
                "profile": profile,
                "medical_conditions": conditions,
                "risk_comparison": risks,
                "focus_summary": simulation_summary,
                "normalization": normalization,
                "drivers": DiseaseSimulationService._key_drivers(
                    focus,
                    baseline_metrics,
                    simulation_metrics,
                    current_scores,
                    simulated_scores,
                ),
                "recommendations": recommendations[:5],
                "assumptions": baseline_context["assumptions"],
            },
        }
