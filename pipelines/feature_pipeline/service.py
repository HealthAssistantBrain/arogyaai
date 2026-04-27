from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev
from typing import Any, Iterable

from sqlalchemy.orm import Session

from models import HealthProfile, User, UserProfile, UserVital, UserVitalTypeEnum, VitalsData, WearableData
from services.sleep_service import SleepService
from pipelines.storage_pipeline.service import StoragePipelineService

LOOKBACK_DAYS = 30
SLEEP_LOOKBACK_DAYS = 14
VITAL_LOOKBACK_DAYS = 7


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None:
            return default
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _mean(values: Iterable[float]) -> float | None:
    data = [float(item) for item in values if item is not None]
    if not data:
        return None
    return float(mean(data))


def _stdev(values: Iterable[float]) -> float | None:
    data = [float(item) for item in values if item is not None]
    if len(data) < 2:
        return None
    return float(pstdev(data))


def _percentile(values: list[float], percentile: float) -> float | None:
    data = sorted(float(item) for item in values if item is not None)
    if not data:
        return None

    if percentile <= 0:
        return data[0]
    if percentile >= 100:
        return data[-1]

    rank = (len(data) - 1) * (percentile / 100.0)
    low = int(rank)
    high = min(len(data) - 1, low + 1)
    weight = rank - low
    return data[low] * (1 - weight) + data[high] * weight


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _age_from_dob(dob) -> int | None:
    if not dob:
        return None

    today = _now_utc().date()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return max(years, 0)


def _bp_category(sys_bp: int | None, dia_bp: int | None) -> str:
    if sys_bp is None or dia_bp is None:
        return "unknown"
    if sys_bp >= 140 or dia_bp >= 90:
        return "stage_2"
    if sys_bp >= 130 or dia_bp >= 80:
        return "stage_1"
    if sys_bp >= 120:
        return "elevated"
    return "normal"


def _sleep_score_from_duration(duration_hours: float | None, hrv: float | None, rhr: float | None) -> float | None:
    if duration_hours is None:
        return None

    duration_component = _clamp((duration_hours / 8.0) * 100.0, 0.0, 100.0)
    hrv_component = _clamp((_safe_float(hrv, 48.0) or 48.0) / 80.0 * 100.0, 0.0, 100.0)
    rhr_value = _safe_float(rhr, 58.0) or 58.0
    rhr_component = _clamp(100.0 - max(0.0, (rhr_value - 45.0) * 4.0), 0.0, 100.0)
    score = duration_component * 0.55 + hrv_component * 0.15 + rhr_component * 0.20 + (100.0 - abs(duration_hours - 8.0) * 10.0) * 0.10
    return round(_clamp(score, 0.0, 100.0), 1)


def _hrv_proxy(heart_rates: list[float], sleep_score: float | None, sleep_hours: float | None) -> float | None:
    if heart_rates:
        avg_hr = _mean(heart_rates) or 60.0
        spread = _stdev(heart_rates) or 0.0
        sleep_bonus = ((sleep_score or 70.0) - 75.0) * 0.25
        duration_bonus = ((sleep_hours or 7.0) - 7.0) * 1.6
        hrv = 78.0 - (avg_hr - 50.0) * 1.35 - spread * 2.2 + sleep_bonus + duration_bonus
        return round(_clamp(hrv, 18.0, 95.0), 1)

    if sleep_score is None and sleep_hours is None:
        return None

    score_component = ((sleep_score or 70.0) - 75.0) * 0.4
    duration_component = ((sleep_hours or 7.0) - 7.0) * 2.0
    return round(_clamp(54.0 + score_component + duration_component, 18.0, 95.0), 1)


def _rhr_proxy(heart_rates: list[float], sleep_score: float | None, sleep_hours: float | None) -> float | None:
    if heart_rates:
        low = _percentile(heart_rates, 20.0)
        if low is None:
            low = _mean(heart_rates) or 58.0
        sleep_penalty = max(0.0, 76.0 - (sleep_score or 76.0)) * 0.04
        duration_penalty = max(0.0, 7.0 - (sleep_hours or 7.0)) * 0.8
        rhr = low + sleep_penalty + duration_penalty
        return round(_clamp(rhr, 45.0, 80.0), 1)

    if sleep_score is None and sleep_hours is None:
        return None

    return round(_clamp(62.0 - max(0.0, (sleep_hours or 7.0) - 7.0) * 1.4 - max(0.0, (sleep_score or 75.0) - 75.0) * 0.1, 45.0, 78.0), 1)


def _cholesterol_proxy(
    bmi: float | None,
    systolic_bp: int | None,
    diastolic_bp: int | None,
    activity_level: int | None,
    sleep_score: float | None,
    age: int | None,
) -> float | None:
    if bmi is None and systolic_bp is None and diastolic_bp is None and activity_level is None and sleep_score is None and age is None:
        return None

    score = 96.0
    if bmi is not None:
        score += max(0.0, bmi - 24.0) * 4.4
    if systolic_bp is not None:
        score += max(0.0, systolic_bp - 118) * 0.42
    if diastolic_bp is not None:
        score += max(0.0, diastolic_bp - 76) * 0.32
    if activity_level is not None:
        score += max(0.0, 8000 - activity_level) / 260.0
    if sleep_score is not None:
        score += max(0.0, 78.0 - sleep_score) * 0.7
    if age is not None:
        score += max(0.0, age - 35) * 0.45

    return round(_clamp(score, 60.0, 190.0), 1)


def _latest_profile(db: Session, user: User) -> HealthProfile | UserProfile | None:
    health_profile = db.query(HealthProfile).filter(HealthProfile.user_id == user.id).first()
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

    if health_profile and user_profile:
        health_updated = _to_utc(getattr(health_profile, "updated_at", None)) or _to_utc(getattr(health_profile, "created_at", None))
        user_updated = _to_utc(getattr(user_profile, "updated_at", None)) or _to_utc(getattr(user_profile, "created_at", None))
        if user_updated and health_updated and user_updated > health_updated:
            return user_profile
        return health_profile

    return health_profile or user_profile


def _recent_heart_rates(db: Session, user: User, days: int = VITAL_LOOKBACK_DAYS) -> list[float]:
    cutoff = _now_utc() - timedelta(days=days)
    values: list[float] = []

    for row in (
        db.query(UserVital)
        .filter(
            UserVital.user_id == user.id,
            UserVital.vital_type == UserVitalTypeEnum.HEART_RATE,
            UserVital.timestamp >= cutoff,
        )
        .order_by(UserVital.timestamp.asc())
        .all()
    ):
        if row.value is not None:
            values.append(float(row.value))

    for row in (
        db.query(VitalsData)
        .filter(
            VitalsData.user_id == user.id,
            VitalsData.recorded_at >= cutoff,
        )
        .order_by(VitalsData.recorded_at.asc())
        .all()
    ):
        if row.heart_rate_bpm is not None:
            values.append(float(row.heart_rate_bpm))

    return values


def _recent_steps(db: Session, user: User, days: int = LOOKBACK_DAYS) -> list[float]:
    cutoff = _now_utc() - timedelta(days=days)
    values: list[float] = []

    for row in (
        db.query(UserVital)
        .filter(
            UserVital.user_id == user.id,
            UserVital.vital_type == UserVitalTypeEnum.STEPS,
            UserVital.timestamp >= cutoff,
        )
        .order_by(UserVital.timestamp.asc())
        .all()
    ):
        if row.value is not None:
            values.append(float(row.value))

    for row in (
        db.query(WearableData)
        .filter(
            WearableData.user_id == user.id,
            WearableData.recorded_at >= cutoff,
        )
        .order_by(WearableData.recorded_at.asc())
        .all()
    ):
        if row.step_count is not None:
            values.append(float(row.step_count))

    return values


def _recent_sleep_rows(db: Session, user: User, days: int = SLEEP_LOOKBACK_DAYS) -> tuple[list[float], list[float], int]:
    cutoff = _now_utc() - timedelta(days=days)
    durations: list[float] = []
    scores: list[int] = []
    source_rows = 0

    for row in (
        db.query(UserVital)
        .filter(
            UserVital.user_id == user.id,
            UserVital.vital_type == UserVitalTypeEnum.SLEEP,
            UserVital.timestamp >= cutoff,
        )
        .order_by(UserVital.timestamp.asc())
        .all()
    ):
        if row.value is not None:
            durations.append(float(row.value))
            source_rows += 1

    for row in (
        db.query(WearableData)
        .filter(
            WearableData.user_id == user.id,
            WearableData.recorded_at >= cutoff,
        )
        .order_by(WearableData.recorded_at.asc())
        .all()
    ):
        if row.sleep_duration_minutes is not None:
            durations.append(float(row.sleep_duration_minutes) / 60.0)
            source_rows += 1
        if row.sleep_score is not None:
            scores.append(int(row.sleep_score))

    return durations, [float(score) for score in scores], source_rows


@dataclass
class FeatureSnapshot:
    avg_hrv: float | None
    avg_rhr: float | None
    sleep_score: float | None
    sleep_duration: float | None
    activity_level: int | None
    bmi: float | None
    systolic_bp: int | None
    diastolic_bp: int | None
    bp_category: str
    age: int | None
    cholesterol_proxy: float | None
    data_points: int
    data_completeness: float
    confidence: float
    latest_observation_at: datetime | None
    source_breakdown: dict[str, int]
    notes: list[str]
    hr_mean_7d: float | None = None
    steps_avg_7d: float | None = None
    sleep_efficiency: float | None = None
    lifestyle_score: float | None = None
    activity_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "avg_hrv": self.avg_hrv,
            "avg_rhr": self.avg_rhr,
            "sleep_score": self.sleep_score,
            "sleep_duration": self.sleep_duration,
            "activity_level": self.activity_level,
            "bmi": self.bmi,
            "systolic_bp": self.systolic_bp,
            "diastolic_bp": self.diastolic_bp,
            "bp_category": self.bp_category,
            "age": self.age,
            "cholesterol_proxy": self.cholesterol_proxy,
            "data_points": self.data_points,
            "data_completeness": self.data_completeness,
            "confidence": self.confidence,
            "latest_observation_at": self.latest_observation_at.isoformat() if self.latest_observation_at else None,
            "source_breakdown": self.source_breakdown,
            "notes": self.notes,
            "hr_mean_7d": self.hr_mean_7d,
            "steps_avg_7d": self.steps_avg_7d,
            "sleep_efficiency": self.sleep_efficiency,
            "lifestyle_score": self.lifestyle_score,
            "activity_score": self.activity_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeatureSnapshot":
        latest_observation_at = data.get("latest_observation_at")
        parsed_latest = None
        if isinstance(latest_observation_at, str) and latest_observation_at:
            try:
                parsed_latest = datetime.fromisoformat(latest_observation_at.replace("Z", "+00:00"))
            except ValueError:
                parsed_latest = None
        elif isinstance(latest_observation_at, datetime):
            parsed_latest = latest_observation_at

        return cls(
            avg_hrv=data.get("avg_hrv"),
            avg_rhr=data.get("avg_rhr"),
            sleep_score=data.get("sleep_score"),
            sleep_duration=data.get("sleep_duration"),
            activity_level=data.get("activity_level"),
            bmi=data.get("bmi"),
            systolic_bp=data.get("systolic_bp"),
            diastolic_bp=data.get("diastolic_bp"),
            bp_category=data.get("bp_category") or "unknown",
            age=data.get("age"),
            cholesterol_proxy=data.get("cholesterol_proxy"),
            data_points=int(data.get("data_points") or 0),
            data_completeness=float(data.get("data_completeness") or 0.0),
            confidence=float(data.get("confidence") or 0.0),
            latest_observation_at=parsed_latest,
            source_breakdown=dict(data.get("source_breakdown") or {}),
            notes=list(data.get("notes") or []),
            hr_mean_7d=data.get("hr_mean_7d"),
            steps_avg_7d=data.get("steps_avg_7d"),
            sleep_efficiency=data.get("sleep_efficiency"),
            lifestyle_score=data.get("lifestyle_score"),
            activity_score=data.get("activity_score"),
        )


class FeaturePipelineService:
    @staticmethod
    def build_feature_snapshot(
        db: Session,
        user: User,
        overrides: dict[str, Any] | None = None,
        *,
        persist: bool = True,
        report_id: str | None = None,
    ) -> FeatureSnapshot:
        profile = _latest_profile(db, user)
        latest_vitals = (
            db.query(VitalsData)
            .filter(VitalsData.user_id == user.id)
            .order_by(VitalsData.recorded_at.desc())
            .first()
        )

        sleep_summary = SleepService.get_sleep_summary(db, user)
        sleep_payload = sleep_summary.get("data") or {}
        sleep_empty = bool(sleep_payload.get("empty"))

        heart_rates = _recent_heart_rates(db, user)
        steps = _recent_steps(db, user)
        sleep_durations, wearable_sleep_scores, sleep_source_rows = _recent_sleep_rows(db, user)

        avg_hrv = _safe_float(sleep_payload.get("hrv"))
        avg_rhr = _safe_float(sleep_payload.get("rhr"))
        sleep_score = _safe_float(sleep_payload.get("sleep_score"))
        sleep_duration = _safe_float(sleep_payload.get("duration"))

        if avg_hrv is None:
            avg_hrv = _hrv_proxy(heart_rates, sleep_score, sleep_duration)
        if avg_rhr is None:
            avg_rhr = _rhr_proxy(heart_rates, sleep_score, sleep_duration)
        if sleep_score is None:
            if wearable_sleep_scores:
                sleep_score = round(float(mean(wearable_sleep_scores)), 1)
            elif sleep_durations:
                sleep_score = _sleep_score_from_duration(_mean(sleep_durations), avg_hrv, avg_rhr)
        if sleep_duration is None and sleep_durations:
            sleep_duration = round(float(mean(sleep_durations)), 1)

        activity_level = None
        if steps:
            activity_level = int(round(float(mean(steps))))

        height_cm = _safe_float(getattr(profile, "height_cm", None))
        weight_kg = _safe_float(getattr(profile, "weight_kg", None))
        bmi = None
        if height_cm and weight_kg and height_cm > 0:
            bmi = round(weight_kg / ((height_cm / 100.0) ** 2), 1)

        systolic_bp = _safe_int(getattr(latest_vitals, "blood_pressure_sys", None))
        diastolic_bp = _safe_int(getattr(latest_vitals, "blood_pressure_dia", None))
        bp_category = _bp_category(systolic_bp, diastolic_bp)

        age = _age_from_dob(getattr(profile, "date_of_birth", None))
        if age is None:
            age = _safe_int(getattr(profile, "age", None))
        cholesterol_proxy = _cholesterol_proxy(bmi, systolic_bp, diastolic_bp, activity_level, sleep_score, age)

        source_breakdown = {
            "heart_rate_points": len(heart_rates),
            "step_points": len(steps),
            "sleep_points": len(sleep_durations) + len(wearable_sleep_scores),
            "wearable_sleep_rows": sleep_source_rows,
            "bp_points": 1 if systolic_bp is not None or diastolic_bp is not None else 0,
        }
        data_points = sum(source_breakdown.values())
        measured_fields = [
            avg_hrv is not None,
            avg_rhr is not None,
            sleep_score is not None,
            sleep_duration is not None,
            activity_level is not None,
            bmi is not None,
            systolic_bp is not None,
            diastolic_bp is not None,
            age is not None,
            cholesterol_proxy is not None,
        ]
        data_completeness = round(sum(1 for field in measured_fields if field) / len(measured_fields), 2)
        latest_candidates = [
            _to_utc(getattr(latest_vitals, "recorded_at", None)),
        ]
        sleep_last = sleep_summary.get("last_updated")
        if sleep_last:
            try:
                latest_candidates.append(_to_utc(datetime.fromisoformat(str(sleep_last).replace("Z", "+00:00"))))
            except ValueError:
                pass
        latest_observation_at = max([candidate for candidate in latest_candidates if candidate is not None], default=None)

        notes: list[str] = []
        if sleep_empty and not sleep_durations and not wearable_sleep_scores:
            notes.append("Sleep metrics were inferred from heart-rate recovery patterns because direct sleep data was not available.")
        if avg_hrv is None:
            notes.append("HRV could not be established from the available time-series data.")
        if systolic_bp is None or diastolic_bp is None:
            notes.append("No recent blood pressure reading was found, so BP-based scoring leans on other cardiovascular signals.")
        if bmi is None:
            notes.append("BMI could not be calculated because height or weight is missing in the profile.")

        recency_hours = None
        if latest_observation_at is not None:
            recency_hours = max(0.0, (_now_utc() - latest_observation_at).total_seconds() / 3600.0)
        recency_factor = 1.0
        if recency_hours is not None:
            recency_factor = _clamp(1.0 - (recency_hours / 168.0), 0.15, 1.0)

        confidence = round(_clamp(42.0 + data_completeness * 38.0 + recency_factor * 20.0, 18.0, 96.0), 1)

        hr_mean_7d = _mean(heart_rates)
        steps_avg_7d = _mean(steps)
        sleep_efficiency = None
        if sleep_duration is not None:
            sleep_efficiency = round(_clamp((sleep_duration / 8.0) * 100.0, 0.0, 100.0), 1)
        elif sleep_score is not None:
            sleep_efficiency = round(_clamp(sleep_score, 0.0, 100.0), 1)

        activity_score = None
        if activity_level is not None:
            activity_score = round(_clamp((activity_level / 12000.0) * 100.0, 0.0, 100.0), 1)

        lifestyle_score = None
        if activity_score is not None or sleep_efficiency is not None:
            activity_component = activity_score if activity_score is not None else 55.0
            sleep_component = sleep_efficiency if sleep_efficiency is not None else 55.0
            bmi_component = 100.0
            if bmi is not None:
                bmi_component = _clamp(100.0 - max(0.0, bmi - 24.0) * 3.5, 0.0, 100.0)
            lifestyle_score = round(_clamp(activity_component * 0.4 + sleep_component * 0.4 + bmi_component * 0.2, 0.0, 100.0), 1)

        snapshot = FeatureSnapshot(
            avg_hrv=avg_hrv,
            avg_rhr=avg_rhr,
            sleep_score=sleep_score,
            sleep_duration=sleep_duration,
            activity_level=activity_level,
            bmi=bmi,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            bp_category=bp_category,
            age=age,
            cholesterol_proxy=cholesterol_proxy,
            data_points=data_points,
            data_completeness=data_completeness,
            confidence=confidence,
            latest_observation_at=latest_observation_at,
            source_breakdown=source_breakdown,
            notes=notes,
            hr_mean_7d=hr_mean_7d,
            steps_avg_7d=steps_avg_7d,
            sleep_efficiency=sleep_efficiency,
            lifestyle_score=lifestyle_score,
            activity_score=activity_score,
        )

        if overrides:
            for key, value in overrides.items():
                if hasattr(snapshot, key):
                    setattr(snapshot, key, value)

            if any(key in overrides for key in {"activity_level", "sleep_score", "sleep_duration", "bmi"}):
                if snapshot.activity_level is not None:
                    snapshot.activity_score = round(_clamp((float(snapshot.activity_level) / 12000.0) * 100.0, 0.0, 100.0), 1)
                if snapshot.sleep_duration is not None:
                    snapshot.sleep_efficiency = round(_clamp((float(snapshot.sleep_duration) / 8.0) * 100.0, 0.0, 100.0), 1)
                elif snapshot.sleep_score is not None:
                    snapshot.sleep_efficiency = round(_clamp(float(snapshot.sleep_score), 0.0, 100.0), 1)
                if snapshot.activity_score is not None or snapshot.sleep_efficiency is not None:
                    activity_component = snapshot.activity_score if snapshot.activity_score is not None else 55.0
                    sleep_component = snapshot.sleep_efficiency if snapshot.sleep_efficiency is not None else 55.0
                    bmi_component = 100.0
                    if snapshot.bmi is not None:
                        bmi_component = _clamp(100.0 - max(0.0, float(snapshot.bmi) - 24.0) * 3.5, 0.0, 100.0)
                    snapshot.lifestyle_score = round(_clamp(activity_component * 0.4 + sleep_component * 0.4 + bmi_component * 0.2, 0.0, 100.0), 1)

        if persist:
            StoragePipelineService.store_feature_snapshot(db, user, snapshot, report_id=report_id)

        return snapshot
