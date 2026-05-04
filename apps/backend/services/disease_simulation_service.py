from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy.orm import Session

from models import MedicalHistory, User, UserProfile
from pipelines.feature_pipeline.service import FeaturePipelineService, FeatureSnapshot
from pipelines.ml_pipeline.inference import MLPipelineInference
from pipelines.ml_pipeline.model_loader import ModelLoader
from pipelines.ml_pipeline.preprocess import build_feature_vector
from pipelines.ml_pipeline.shap_explainer import ShapExplainer
from services.clinical_insight_service import ClinicalInsightService
from services.notification_service import trigger_notification_sync

logger = logging.getLogger("uvicorn.error")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    numeric = _safe_float(value)
    if numeric is None:
        return default
    return int(round(numeric))


def _safe_bool(value: Any, default: bool | None = None) -> bool | None:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "smoker"}:
        return True
    if normalized in {"0", "false", "no", "n", "non-smoker", "nonsmoker"}:
        return False
    return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _normalize_focus(value: str | None) -> str:
    aliases = {
        "cardio": "cardiovascular",
        "cardiovascular": "cardiovascular",
        "heart": "cardiovascular",
        "diabetes": "diabetes",
        "glucose": "diabetes",
        "metabolic": "diabetes",
        "respiratory": "respiratory",
        "lungs": "respiratory",
        "lung": "respiratory",
    }
    return aliases.get(str(value or "cardiovascular").strip().lower(), "cardiovascular")


def _age_from_dob(dob: Any) -> int | None:
    if not dob:
        return None
    today = _utc_now().date()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return max(years, 0)


@dataclass
class SimulatorInputs:
    sleep: float
    steps: int
    heart_rate: int
    systolic_bp: int
    diastolic_bp: int
    weight: float
    bmi: float | None = None
    glucose: float | None = None
    hba1c: float | None = None
    diet_score: float | None = None
    spo2: float | None = None
    resp_rate: int | None = None
    activity: float | None = None
    air_quality: float | None = None
    smoking: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "sleep": round(self.sleep, 1),
            "steps": int(self.steps),
            "heart_rate": int(self.heart_rate),
            "systolic_bp": int(self.systolic_bp),
            "diastolic_bp": int(self.diastolic_bp),
            "bmi": round(float(self.bmi), 1) if self.bmi is not None else None,
            "glucose": round(float(self.glucose), 1) if self.glucose is not None else None,
            "hba1c": round(float(self.hba1c), 1) if self.hba1c is not None else None,
            "diet_score": round(float(self.diet_score), 1) if self.diet_score is not None else None,
            "spo2": round(float(self.spo2), 1) if self.spo2 is not None else None,
            "resp_rate": int(self.resp_rate) if self.resp_rate is not None else None,
            "activity": round(float(self.activity), 1) if self.activity is not None else None,
            "air_quality": round(float(self.air_quality), 1) if self.air_quality is not None else None,
            "smoking": bool(self.smoking) if self.smoking is not None else None,
        }


class DiseaseSimulationService:
    NORMALIZATION_RANGES = {
        "sleep": (4.0, 10.0),
        "steps": (2000.0, 15000.0),
        "heart_rate": (45.0, 110.0),
        "systolic_bp": (90.0, 180.0),
        "diastolic_bp": (55.0, 110.0),
        "weight": (40.0, 140.0),
        "activity": (0.0, 120.0),
        "air_quality": (0.0, 250.0),
    }

    @staticmethod
    def _latest_profile(db: Session, user: User) -> UserProfile | None:
        return db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

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
    def _weight_from_profile(profile: UserProfile | None) -> float:
        return _safe_float(getattr(profile, "weight_kg", None), 72.0) or 72.0

    @staticmethod
    def _height_from_profile(profile: UserProfile | None) -> float:
        return _safe_float(getattr(profile, "height_cm", None), 170.0) or 170.0

    @staticmethod
    def _healthy_weight_range(height_cm: float) -> tuple[float, float]:
        height_m = max(height_cm, 120.0) / 100.0
        return (18.5 * (height_m**2), 24.9 * (height_m**2))

    @staticmethod
    def _bmi(height_cm: float, weight: float) -> float:
        height_m = max(height_cm, 120.0) / 100.0
        return round(weight / (height_m**2), 1)

    @staticmethod
    def _normalize_value(metric: str, value: float) -> float:
        minimum, maximum = DiseaseSimulationService.NORMALIZATION_RANGES[metric]
        if maximum <= minimum:
            return 0.0
        return _clamp((float(value) - minimum) / (maximum - minimum), 0.0, 1.0)

    @staticmethod
    def _bmi_risk(bmi: float) -> float:
        if bmi < 18.5:
            return _clamp((18.5 - bmi) / 4.0, 0.0, 1.0)
        if bmi <= 24.9:
            return 0.0
        return _clamp((bmi - 24.9) / 10.0, 0.0, 1.0)

    @staticmethod
    def _bp_risk(systolic_bp: float, diastolic_bp: float) -> float:
        systolic_component = _clamp((systolic_bp - 120.0) / 40.0, 0.0, 1.0)
        diastolic_component = _clamp((diastolic_bp - 80.0) / 20.0, 0.0, 1.0)
        return _clamp(max(systolic_component, diastolic_component), 0.0, 1.0)

    @staticmethod
    def _heart_rate_risk(heart_rate: float) -> float:
        if heart_rate <= 80:
            return _clamp((heart_rate - 55.0) / 25.0, 0.0, 0.4)
        return _clamp(0.4 + ((heart_rate - 80.0) / 20.0) * 0.6, 0.0, 1.0)

    @staticmethod
    def _weight_factor(weight: float, height_cm: float) -> float:
        low, high = DiseaseSimulationService._healthy_weight_range(height_cm)
        if weight < low:
            return _clamp((low - weight) / max(low * 0.25, 1.0), 0.0, 1.0)
        if weight <= high:
            return 0.0
        return _clamp((weight - high) / max(high * 0.35, 1.0), 0.0, 1.0)

    @staticmethod
    def _glucose_risk(glucose: float | None) -> float:
        if glucose is None:
            return 0.0
        if glucose < 100:
            return 0.0
        return _clamp((glucose - 100.0) / 40.0, 0.0, 1.0)

    @staticmethod
    def _hba1c_risk(hba1c: float | None) -> float:
        if hba1c is None:
            return 0.0
        if hba1c < 5.7:
            return 0.0
        return _clamp((hba1c - 5.7) / 1.8, 0.0, 1.0)

    @staticmethod
    def _spo2_risk(spo2: float | None) -> float:
        if spo2 is None or spo2 >= 95:
            return 0.0
        return _clamp((95.0 - spo2) / 7.0, 0.0, 1.0)

    @staticmethod
    def _resp_rate_risk(resp_rate: float | None) -> float:
        if resp_rate is None:
            return 0.0
        if 12 <= resp_rate <= 20:
            return 0.0
        if resp_rate > 20:
            return _clamp((resp_rate - 20.0) / 12.0, 0.0, 1.0)
        return _clamp((12.0 - resp_rate) / 6.0, 0.0, 1.0)

    @staticmethod
    def _diet_risk(diet_score: float | None) -> float:
        if diet_score is None:
            return 0.0
        return 1.0 - _clamp(diet_score / 100.0, 0.0, 1.0)

    @staticmethod
    def _air_quality_risk(air_quality: float | None) -> float:
        if air_quality is None:
            return 0.0
        if air_quality <= 50:
            return 0.0
        return _clamp((air_quality - 50.0) / 150.0, 0.0, 1.0)

    @staticmethod
    def _build_inputs(
        feature_snapshot: FeatureSnapshot,
        profile: UserProfile | None,
        simulation: dict[str, Any] | None = None,
    ) -> SimulatorInputs:
        overrides = simulation or {}
        height_cm = DiseaseSimulationService._height_from_profile(profile)
        baseline_weight = DiseaseSimulationService._weight_from_profile(profile)
        baseline_bmi = _safe_float(feature_snapshot.bmi)
        if baseline_bmi is None:
            baseline_bmi = DiseaseSimulationService._bmi(height_cm, baseline_weight)

        bmi_override = _safe_float(overrides.get("bmi"))
        weight_override = _safe_float(overrides.get("weight"))
        weight = weight_override if weight_override is not None else baseline_weight
        if bmi_override is not None and weight_override is None:
            weight = bmi_override * ((max(height_cm, 120.0) / 100.0) ** 2)

        sleep = _safe_float(overrides.get("sleep"), feature_snapshot.sleep_duration) or 7.0
        steps = _safe_int(overrides.get("steps"), feature_snapshot.activity_level) or 7000
        heart_rate = _safe_int(
            overrides.get("heart_rate"),
            feature_snapshot.avg_rhr or feature_snapshot.hr_mean_7d,
        ) or 72
        systolic_bp = _safe_int(overrides.get("systolic_bp"), feature_snapshot.systolic_bp) or 120
        diastolic_bp = _safe_int(overrides.get("diastolic_bp"), feature_snapshot.diastolic_bp) or 80
        if bmi_override is not None:
            bmi = bmi_override
        elif weight_override is not None:
            bmi = DiseaseSimulationService._bmi(height_cm, weight)
        else:
            bmi = baseline_bmi
        glucose = _safe_float(overrides.get("glucose"), feature_snapshot.glucose) or 90.0
        hba1c = _safe_float(overrides.get("hba1c"), 5.4) or 5.4
        diet_score = _safe_float(overrides.get("diet_score"), 70.0) or 70.0
        spo2 = _safe_float(overrides.get("spo2"), 97.0) or 97.0
        resp_rate = _safe_int(overrides.get("resp_rate"), 16) or 16
        activity = _safe_float(overrides.get("activity"), round((float(steps) / 100.0), 1)) or 70.0
        air_quality = _safe_float(overrides.get("air_quality"), 50.0) or 50.0
        smoking = _safe_bool(overrides.get("smoking"), _safe_bool(getattr(profile, "smoking", None), False))

        return SimulatorInputs(
            sleep=_clamp(float(sleep), 4.0, 10.0),
            steps=int(_clamp(float(steps), 1500.0, 20000.0)),
            heart_rate=int(_clamp(float(heart_rate), 45.0, 140.0)),
            systolic_bp=int(_clamp(float(systolic_bp), 90.0, 190.0)),
            diastolic_bp=int(_clamp(float(diastolic_bp), 55.0, 120.0)),
            weight=_clamp(float(weight), 35.0, 180.0),
            bmi=_clamp(float(bmi), 12.0, 60.0),
            glucose=_clamp(float(glucose), 60.0, 260.0),
            hba1c=_clamp(float(hba1c), 4.0, 14.0),
            diet_score=_clamp(float(diet_score), 0.0, 100.0),
            spo2=_clamp(float(spo2), 70.0, 100.0),
            resp_rate=int(_clamp(float(resp_rate), 6.0, 40.0)),
            activity=_clamp(float(activity), 0.0, 180.0),
            air_quality=_clamp(float(air_quality), 0.0, 500.0),
            smoking=bool(smoking),
        )

    @staticmethod
    def _feature_payload(
        *,
        baseline_snapshot: FeatureSnapshot,
        profile: UserProfile | None,
        inputs: SimulatorInputs,
    ) -> dict[str, Any]:
        height_cm = DiseaseSimulationService._height_from_profile(profile)
        bmi = _safe_float(inputs.bmi, DiseaseSimulationService._bmi(height_cm, inputs.weight)) or 24.0
        sleep_efficiency = round(_clamp((inputs.sleep / 8.0) * 100.0, 0.0, 100.0), 1)
        activity_score = round(_clamp((inputs.steps / 12000.0) * 100.0, 0.0, 100.0), 1)
        bmi_component = round(_clamp(100.0 - DiseaseSimulationService._bmi_risk(bmi) * 100.0, 0.0, 100.0), 1)
        lifestyle_score = round(
            _clamp(activity_score * 0.4 + sleep_efficiency * 0.4 + bmi_component * 0.2, 0.0, 100.0),
            1,
        )
        profile_age = _age_from_dob(getattr(profile, "date_of_birth", None))
        if profile_age is None:
            profile_age = _safe_int(getattr(profile, "age", None))

        payload = baseline_snapshot.to_dict()
        payload.update(
            {
                "sleep": inputs.sleep,
                "steps": inputs.steps,
                "heart_rate": inputs.heart_rate,
                "weight": inputs.weight,
                "height_cm": height_cm,
                "sleep_duration": inputs.sleep,
                "activity_level": inputs.steps,
                "avg_rhr": float(inputs.heart_rate),
                "hr_mean_7d": float(inputs.heart_rate),
                "steps_avg_7d": float(inputs.steps),
                "sleep_efficiency": sleep_efficiency,
                "activity_score": activity_score,
                "lifestyle_score": lifestyle_score,
                "systolic_bp": int(inputs.systolic_bp),
                "diastolic_bp": int(inputs.diastolic_bp),
                "bmi": bmi,
                "glucose": inputs.glucose,
                "hba1c": inputs.hba1c,
                "diet_score": inputs.diet_score,
                "spo2": inputs.spo2,
                "resp_rate": inputs.resp_rate,
                "activity": inputs.activity,
                "air_quality": inputs.air_quality,
                "smoking": 1.0 if inputs.smoking else 0.0,
                "age": profile_age,
            }
        )
        return payload

    @staticmethod
    def _fallback_overall_probability(feature_payload: dict[str, Any]) -> tuple[float, dict[str, float]]:
        height_cm = _safe_float(feature_payload.get("height_cm"), DiseaseSimulationService._height_from_profile(None)) or 170.0
        weight = _safe_float(feature_payload.get("weight"), 72.0) or 72.0
        bmi = _safe_float(feature_payload.get("bmi"), DiseaseSimulationService._bmi(height_cm, weight)) or 24.0
        systolic_bp = _safe_float(feature_payload.get("systolic_bp"), 120.0) or 120.0
        diastolic_bp = _safe_float(feature_payload.get("diastolic_bp"), 80.0) or 80.0
        steps = _safe_float(feature_payload.get("activity_level") or feature_payload.get("steps"), 7000.0) or 7000.0
        sleep = _safe_float(feature_payload.get("sleep_duration") or feature_payload.get("sleep"), 7.0) or 7.0
        heart_rate = _safe_float(feature_payload.get("avg_rhr") or feature_payload.get("heart_rate"), 72.0) or 72.0

        bmi_risk = DiseaseSimulationService._bmi_risk(bmi)
        bp_risk = DiseaseSimulationService._bp_risk(systolic_bp, diastolic_bp)
        activity_inverse = 1.0 - DiseaseSimulationService._normalize_value("steps", steps)
        sleep_inverse = 1.0 - DiseaseSimulationService._normalize_value("sleep", sleep)
        heart_rate_risk = DiseaseSimulationService._heart_rate_risk(heart_rate)
        weight_factor = DiseaseSimulationService._weight_factor(weight, height_cm)
        respiratory_activity = _safe_float(feature_payload.get("activity"))
        respiratory_activity_inverse = (
            1.0 - DiseaseSimulationService._normalize_value("activity", respiratory_activity)
            if respiratory_activity is not None
            else activity_inverse
        )

        overall = (
            0.25 * bmi_risk
            + 0.20 * bp_risk
            + 0.20 * activity_inverse
            + 0.15 * sleep_inverse
            + 0.10 * heart_rate_risk
            + 0.10 * weight_factor
        )
        return _clamp(overall, 0.0, 1.0), {
            "bmi_risk": round(bmi_risk, 4),
            "bp_risk": round(bp_risk, 4),
            "activity_inverse": round(activity_inverse, 4),
            "sleep_inverse": round(sleep_inverse, 4),
            "heart_rate_risk": round(heart_rate_risk, 4),
            "weight_factor": round(weight_factor, 4),
            "respiratory_activity_inverse": round(respiratory_activity_inverse, 4),
        }

    @staticmethod
    def _hybrid_scores(
        *,
        feature_payload: dict[str, Any],
        ml_probability: float | None,
    ) -> tuple[dict[str, float], dict[str, Any]]:
        overall_fallback, components = DiseaseSimulationService._fallback_overall_probability(feature_payload)
        bmi_risk = components["bmi_risk"]
        bp_risk = components["bp_risk"]
        activity_inverse = components["activity_inverse"]
        sleep_inverse = components["sleep_inverse"]
        heart_rate_risk = components["heart_rate_risk"]
        weight_factor = components["weight_factor"]
        respiratory_activity_inverse = components.get("respiratory_activity_inverse", activity_inverse)
        glucose_risk = DiseaseSimulationService._glucose_risk(_safe_float(feature_payload.get("glucose")))
        hba1c_risk = DiseaseSimulationService._hba1c_risk(_safe_float(feature_payload.get("hba1c")))
        diet_risk = DiseaseSimulationService._diet_risk(_safe_float(feature_payload.get("diet_score")))
        spo2_risk = DiseaseSimulationService._spo2_risk(_safe_float(feature_payload.get("spo2")))
        resp_rate_risk = DiseaseSimulationService._resp_rate_risk(_safe_float(feature_payload.get("resp_rate")))
        air_quality_risk = DiseaseSimulationService._air_quality_risk(_safe_float(feature_payload.get("air_quality")))
        smoking_risk = 0.75 if _safe_bool(feature_payload.get("smoking"), False) else 0.0

        cardio_rule = _clamp(
            0.30 * bp_risk
            + 0.20 * heart_rate_risk
            + 0.15 * activity_inverse
            + 0.15 * sleep_inverse
            + 0.10 * bmi_risk
            + 0.10 * weight_factor,
            0.0,
            1.0,
        )
        diabetes_rule = _clamp(
            0.25 * bmi_risk
            + 0.20 * activity_inverse
            + 0.15 * sleep_inverse
            + 0.15 * glucose_risk
            + 0.15 * hba1c_risk
            + 0.05 * diet_risk
            + 0.05 * bp_risk,
            0.0,
            1.0,
        )
        respiratory_rule = _clamp(
            0.25 * spo2_risk
            + 0.20 * resp_rate_risk
            + 0.15 * respiratory_activity_inverse
            + 0.15 * air_quality_risk
            + 0.10 * smoking_risk
            + 0.10 * sleep_inverse
            + 0.05 * weight_factor,
            0.0,
            1.0,
        )

        if ml_probability is None:
            scoring_mode = "deterministic_fallback"
            return (
                {
                    "cardiovascular": round(cardio_rule, 4),
                    "diabetes": round(diabetes_rule, 4),
                    "respiratory": round(respiratory_rule, 4),
                },
                {
                    "mode": scoring_mode,
                    "ml_probability": None,
                    "fallback_probability": round(overall_fallback, 4),
                    "components": components,
                    "glucose_risk": round(glucose_risk, 4),
                    "hba1c_risk": round(hba1c_risk, 4),
                    "diet_risk": round(diet_risk, 4),
                    "spo2_risk": round(spo2_risk, 4),
                    "resp_rate_risk": round(resp_rate_risk, 4),
                    "air_quality_risk": round(air_quality_risk, 4),
                    "smoking_risk": round(smoking_risk, 4),
                },
            )

        scoring_mode = "hybrid_ml_plus_rules"
        return (
            {
                "cardiovascular": round(_clamp(0.65 * ml_probability + 0.35 * cardio_rule, 0.0, 1.0), 4),
                "diabetes": round(_clamp(0.65 * ml_probability + 0.35 * diabetes_rule, 0.0, 1.0), 4),
                "respiratory": round(_clamp(0.55 * ml_probability + 0.45 * respiratory_rule, 0.0, 1.0), 4),
            },
            {
                "mode": scoring_mode,
                "ml_probability": round(ml_probability, 4),
                "fallback_probability": round(overall_fallback, 4),
                "components": components,
                "glucose_risk": round(glucose_risk, 4),
                "hba1c_risk": round(hba1c_risk, 4),
                "diet_risk": round(diet_risk, 4),
                "spo2_risk": round(spo2_risk, 4),
                "resp_rate_risk": round(resp_rate_risk, 4),
                "air_quality_risk": round(air_quality_risk, 4),
                "smoking_risk": round(smoking_risk, 4),
            },
        )

    @staticmethod
    def _predict_with_model(feature_payload: dict[str, Any]) -> tuple[float | None, list[dict[str, Any]], str | None]:
        loader = ModelLoader(auto_train_if_missing=False)
        loaded_model = loader.load()
        if loaded_model is None:
            return None, [], None

        inference = MLPipelineInference(loaded_model)
        result = inference.predict(feature_payload)
        if result is None:
            return None, [], None

        features = build_feature_vector(feature_payload, loaded_model.feature_names)
        try:
            shap_values = ShapExplainer.explain(
                feature_payload,
                loaded_model=loaded_model,
                features=features,
            )
        except Exception:
            shap_values = []

        return result.score, shap_values, result.model_version

    @staticmethod
    def _risk_comparison(current_risk: dict[str, float], simulated_risk: dict[str, float]) -> list[dict[str, Any]]:
        labels = {
            "cardiovascular": "Cardiovascular",
            "diabetes": "Diabetes",
            "respiratory": "Respiratory",
        }
        items: list[dict[str, Any]] = []
        for key in ("cardiovascular", "diabetes", "respiratory"):
            current_score = current_risk.get(key, 0.0)
            simulated_score = simulated_risk.get(key, 0.0)
            delta = simulated_score - current_score
            items.append(
                {
                    "key": key,
                    "label": labels[key],
                    "current_score": round(current_score, 4),
                    "simulated_score": round(simulated_score, 4),
                    "current_risk": round(current_score * 100.0, 1),
                    "simulated_risk": round(simulated_score * 100.0, 1),
                    "delta": round(delta * 100.0, 1),
                }
            )
        return items

    @staticmethod
    def _normalization_summary(focus: str, current_risk: dict[str, float], simulated_risk: dict[str, float], timeframe_months: int) -> dict[str, Any]:
        before = current_risk.get(focus, 0.0)
        after = simulated_risk.get(focus, 0.0)
        reduction = round((before - after) * 100.0, 1)

        if after < 0.3:
            likelihood = "High"
            headline = f"If this pattern is sustained for {timeframe_months} months, {focus.replace('_', ' ')} risk could move closer to a lower-risk range."
        elif after < before:
            likelihood = "Moderate"
            headline = f"The simulation lowers {focus.replace('_', ' ')} risk, but residual risk remains clinically relevant."
        else:
            likelihood = "Low"
            headline = f"The simulated pattern does not improve {focus.replace('_', ' ')} risk and may require stronger changes."

        return {
            "can_return_to_normal": after < 0.3,
            "likelihood": likelihood,
            "headline": headline,
            "risk_reduction_points": reduction,
        }

    @staticmethod
    def build_baseline(db: Session, user: User) -> dict[str, Any]:
        profile = DiseaseSimulationService._latest_profile(db, user)
        feature_snapshot = FeaturePipelineService.build_feature_snapshot(db, user, persist=False)
        baseline = DiseaseSimulationService._build_inputs(feature_snapshot, profile)
        conditions = DiseaseSimulationService._conditions(db, user)
        lowered_conditions = " ".join(item.lower() for item in conditions)

        condition_hints: list[str] = []
        if any(keyword in lowered_conditions for keyword in ("heart", "cardio", "hypertension", "bp")):
            condition_hints.append("cardiovascular")
        if any(keyword in lowered_conditions for keyword in ("diabetes", "glucose", "sugar", "insulin")):
            condition_hints.append("diabetes")
        if any(keyword in lowered_conditions for keyword in ("asthma", "copd", "respiratory", "lung")):
            condition_hints.append("respiratory")

        focus_options = list(dict.fromkeys(condition_hints + ["cardiovascular", "diabetes", "respiratory"]))
        height_cm = DiseaseSimulationService._height_from_profile(profile)
        weight = DiseaseSimulationService._weight_from_profile(profile)
        bmi = DiseaseSimulationService._bmi(height_cm, weight)

        return {
            "baseline": baseline,
            "profile": {
                "age": (
                    _age_from_dob(getattr(profile, "date_of_birth", None))
                    if profile and getattr(profile, "date_of_birth", None)
                    else _safe_int(getattr(profile, "age", None)) if profile else None
                ),
                "height_cm": round(height_cm, 1),
                "weight_kg": round(weight, 1),
                "bmi": bmi,
            },
            "feature_snapshot": feature_snapshot.to_dict(),
            "conditions": conditions,
            "focus_options": focus_options,
            "assumptions": [
                "Scenario scoring uses the latest stored feature snapshot as the physiological baseline.",
                "Calibrated XGBoost probability is used when the model artifact is available; otherwise an explainable weighted fallback score is used.",
                "Respiratory, cardiovascular, and diabetes outputs combine the shared ML signal with condition-specific rule adjustments.",
            ],
        }

    @staticmethod
    def simulate(db: Session, user: User, payload: Any) -> dict[str, Any]:
        baseline_context = DiseaseSimulationService.build_baseline(db, user)
        baseline_feature_snapshot = FeatureSnapshot.from_dict(baseline_context["feature_snapshot"])
        profile = DiseaseSimulationService._latest_profile(db, user)

        focus_condition = _normalize_focus(getattr(payload, "focus_condition", None))
        timeframe_months = int(_clamp(float(getattr(payload, "timeframe_months", 6) or 6), 1.0, 12.0))
        simulation_payload = getattr(getattr(payload, "simulation", None), "model_dump", lambda: {})()

        baseline_inputs = baseline_context["baseline"]
        scenario_inputs = DiseaseSimulationService._build_inputs(
            baseline_feature_snapshot,
            profile,
            simulation=simulation_payload,
        )

        baseline_feature_payload = DiseaseSimulationService._feature_payload(
            baseline_snapshot=baseline_feature_snapshot,
            profile=profile,
            inputs=baseline_inputs,
        )
        scenario_feature_payload = DiseaseSimulationService._feature_payload(
            baseline_snapshot=baseline_feature_snapshot,
            profile=profile,
            inputs=scenario_inputs,
        )

        baseline_ml_probability, baseline_shap_values, baseline_model_version = DiseaseSimulationService._predict_with_model(
            baseline_feature_payload
        )
        scenario_ml_probability, scenario_shap_values, scenario_model_version = DiseaseSimulationService._predict_with_model(
            scenario_feature_payload
        )

        current_risk, current_meta = DiseaseSimulationService._hybrid_scores(
            feature_payload=baseline_feature_payload,
            ml_probability=baseline_ml_probability,
        )
        simulated_risk, simulated_meta = DiseaseSimulationService._hybrid_scores(
            feature_payload=scenario_feature_payload,
            ml_probability=scenario_ml_probability,
        )
        delta_map = {
            key: round(simulated_risk[key] - current_risk[key], 4)
            for key in ("cardiovascular", "diabetes", "respiratory")
        }

        clinical_payload = ClinicalInsightService.enrich_payload(
            feature_payload=scenario_feature_payload,
            risk_map=simulated_risk,
            shap_values=scenario_shap_values or baseline_shap_values,
            focus_condition=focus_condition,
            delta_map=delta_map,
        )

        focus_outcome = clinical_payload["outcome"]
        response_data = {
            "focus_condition": focus_condition,
            "timeframe_months": timeframe_months,
            "baseline": baseline_inputs.as_dict(),
            "simulation": scenario_inputs.as_dict(),
            "profile": baseline_context["profile"],
            "medical_conditions": baseline_context["conditions"],
            "current_risk": current_risk,
            "simulated_risk": simulated_risk,
            "delta": delta_map,
            "risk_comparison": DiseaseSimulationService._risk_comparison(current_risk, simulated_risk),
            "focus_summary": focus_outcome["summary"],
            "normalization": DiseaseSimulationService._normalization_summary(
                focus_condition,
                current_risk,
                simulated_risk,
                timeframe_months,
            ),
            "outcome": focus_outcome,
            "summary": clinical_payload["summary"],
            "drivers": clinical_payload["key_drivers"],
            "key_drivers": clinical_payload["key_drivers"],
            "symptoms": clinical_payload["symptoms"],
            "possible_conditions": clinical_payload["possible_conditions"],
            "recommendations": clinical_payload["recommendations"],
            "assumptions": baseline_context["assumptions"],
            "feature_snapshot": scenario_feature_payload,
            "scoring": {
                "current": current_meta,
                "simulated": simulated_meta,
                "model_version": scenario_model_version or baseline_model_version,
            },
        }

        try:
            trigger_notification_sync(
                user_id=str(user.id),
                event_type="simulation",
                title="Simulation Completed",
                message="Your risk simulation results are ready.",
                data={
                    "focus_condition": focus_condition,
                    "timeframe_months": timeframe_months,
                    "summary": clinical_payload["summary"],
                    "url": "/simulator",
                },
            )
        except Exception as exc:
            logger.exception("Simulation notification failed for user=%s: %s", user.id, exc)

        return {
            "success": True,
            "status": "ready",
            "source": simulated_meta["mode"],
            "error": None,
            "data": response_data,
        }
