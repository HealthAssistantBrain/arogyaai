from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from core.config import settings
from models import GoogleFitConnection, User, UserVital, UserVitalTypeEnum, VitalsData, WearableData


SLEEP_HISTORY_RANGE_DAYS = {
    "24h": 7,
    "7d": 7,
    "30d": 30,
}


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
    data = [float(value) for value in values if value is not None]
    if not data:
        return None
    return float(mean(data))


def _stdev(values: Iterable[float]) -> float | None:
    data = [float(value) for value in values if value is not None]
    if len(data) < 2:
        return None
    return float(pstdev(data))


def _percentile(values: list[float], percentile: float) -> float | None:
    data = sorted(float(value) for value in values if value is not None)
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


def _format_short_day(ts: datetime, tzinfo: ZoneInfo) -> str:
    return ts.astimezone(tzinfo).strftime("%b %d")


def _format_date(ts: datetime, tzinfo: ZoneInfo) -> str:
    return ts.astimezone(tzinfo).date().isoformat()


def _format_time(ts: datetime, tzinfo: ZoneInfo) -> str:
    return ts.astimezone(tzinfo).strftime("%I:%M %p").lstrip("0")


def _sleep_hours_from_user_vital(row: UserVital) -> float | None:
    if row.value is None:
        return None
    try:
        value = float(row.value)
    except (TypeError, ValueError):
        return None

    unit = str(row.unit or "").strip().lower()
    if unit in {"minutes", "minute", "min", "mins"}:
        return value / 60.0
    return value


def _sleep_stage_profile(duration_hours: float, sleep_score: float) -> dict[str, float]:
    deep_raw = 18.0 + (duration_hours - 7.0) * 1.8 + (sleep_score - 75.0) * 0.12
    rem_raw = 22.0 + (duration_hours - 7.0) * 1.0 + (sleep_score - 75.0) * 0.10
    awake_raw = 6.0 + max(0.0, 7.5 - duration_hours) * 2.0 + max(0.0, 78.0 - sleep_score) * 0.08
    light_raw = max(20.0, 100.0 - deep_raw - rem_raw - awake_raw)

    total = deep_raw + rem_raw + light_raw + awake_raw
    if total <= 0:
        return {"deep": 20.0, "rem": 20.0, "light": 50.0, "awake": 10.0}

    deep = round(deep_raw / total * 100.0, 1)
    rem = round(rem_raw / total * 100.0, 1)
    light = round(light_raw / total * 100.0, 1)
    awake = round(max(2.0, 100.0 - deep - rem - light), 1)

    total_pct = deep + rem + light + awake
    if round(total_pct, 1) != 100.0:
        light = round(light + (100.0 - total_pct), 1)

    return {
        "deep": deep,
        "rem": rem,
        "light": light,
        "awake": awake,
    }


def _stage_hours(duration_hours: float, stages: dict[str, float]) -> dict[str, float]:
    return {
        stage: round(duration_hours * (percent / 100.0), 2)
        for stage, percent in stages.items()
    }


def _estimate_sleep_score(duration_hours: float, hrv: float | None, rhr: float | None) -> int:
    duration_component = _clamp((duration_hours / 8.0) * 100.0, 0.0, 100.0)
    hrv_component = _clamp((_safe_float(hrv, 48.0) or 48.0) / 80.0 * 100.0, 0.0, 100.0)
    rhr_value = _safe_float(rhr, 58.0) or 58.0
    rhr_component = _clamp(100.0 - max(0.0, (rhr_value - 45.0) * 4.0), 0.0, 100.0)

    score = (
        duration_component * 0.45
        + hrv_component * 0.20
        + rhr_component * 0.25
        + (100.0 - abs(duration_hours - 8.0) * 12.0) * 0.10
    )
    return int(round(_clamp(score, 0.0, 100.0)))


def _estimate_efficiency(duration_hours: float, sleep_score: int, stages: dict[str, float]) -> int:
    awake_pct = stages.get("awake", 0.0)
    efficiency = 86.0 + (sleep_score - 75) * 0.65 + (duration_hours - 7.5) * 2.5 - awake_pct * 0.35
    return int(round(_clamp(efficiency, 50.0, 99.0)))


def _estimate_recovery_score(sleep_score: int, efficiency: int, hrv: float | None, rhr: float | None) -> int:
    hrv_value = _clamp(_safe_float(hrv, 48.0) or 48.0, 18.0, 85.0)
    rhr_value = _safe_float(rhr, 58.0) or 58.0
    hrv_component = (hrv_value / 85.0) * 100.0
    rhr_component = _clamp(100.0 - max(0.0, (rhr_value - 45.0) * 3.0), 0.0, 100.0)
    recovery = sleep_score * 0.45 + efficiency * 0.25 + hrv_component * 0.20 + rhr_component * 0.10
    return int(round(_clamp(recovery, 0.0, 100.0)))


def _estimate_hrv_proxy(values: list[float], duration_hours: float, sleep_score: int) -> int:
    if values:
        avg_hr = _mean(values) or 60.0
        spread = _stdev(values) or 0.0
        hrv = 78.0 - (avg_hr - 50.0) * 1.4 - spread * 2.5
    else:
        hrv = 54.0 + (sleep_score - 75) * 0.35 + (duration_hours - 7.0) * 2.0
    return int(round(_clamp(hrv, 18.0, 85.0)))


def _estimate_rhr(values: list[float], duration_hours: float, sleep_score: int) -> int:
    if values:
        low = _percentile(values, 20.0)
        if low is None:
            low = _mean(values)
        rhr = low or 58.0
    else:
        rhr = 62.0 - (duration_hours - 7.0) * 1.5 - (sleep_score - 75) * 0.12
    return int(round(_clamp(rhr, 45.0, 72.0)))


def _night_key(reference_end: datetime, tzinfo: ZoneInfo) -> str:
    return reference_end.astimezone(tzinfo).date().isoformat()


def _night_window(reference_end: datetime, duration_hours: float) -> tuple[datetime, datetime]:
    wake_time = reference_end
    sleep_start = wake_time - timedelta(hours=max(4.0, min(duration_hours or 8.0, 12.0)))
    return sleep_start, wake_time


def _build_timeline(duration_hours: float, stages: dict[str, float], sleep_start: datetime, wake_time: datetime) -> list[dict[str, Any]]:
    total_points = max(16, min(32, int(round(duration_hours * 4.0))))
    stage_levels = {"deep": 0, "light": 1, "rem": 2, "awake": 3}

    deep_cutoff = stages["deep"] / 100.0
    rem_cutoff = deep_cutoff + (stages["light"] / 100.0) * 0.45
    late_rem_cutoff = 1.0 - (stages["awake"] / 100.0) * 0.65

    points: list[dict[str, Any]] = []
    for index in range(total_points):
        progress = 0.0 if total_points == 1 else index / (total_points - 1)
        if progress < deep_cutoff:
            stage = "deep" if progress < deep_cutoff * 0.72 else "light"
        elif progress < rem_cutoff:
            stage = "light"
        elif progress < late_rem_cutoff:
            stage = "rem"
        else:
            stage = "awake" if progress > 1.0 - max(0.03, stages["awake"] / 120.0) else "light"

        timestamp = sleep_start + timedelta(hours=duration_hours * progress)
        points.append(
            {
                "timestamp": timestamp.isoformat(),
                "offset_minutes": int(round(duration_hours * 60.0 * progress)),
                "stage": stage,
                "stage_level": stage_levels[stage],
                "label": stage.title(),
            }
        )

    return points


def _build_weekly_row(sample: dict[str, Any]) -> dict[str, Any]:
    duration_hours = float(sample.get("duration_hours") or 0.0)
    sleep_score = int(sample.get("sleep_score") or 0)
    stages = _sleep_stage_profile(duration_hours, sleep_score if sleep_score > 0 else 75)
    stage_hours = _stage_hours(duration_hours, stages)
    return {
        "day": sample.get("day_label"),
        "date": sample.get("night_key"),
        "deep": stage_hours["deep"],
        "light": stage_hours["light"],
        "rem": stage_hours["rem"],
        "awake": stage_hours["awake"],
        "duration": round(duration_hours, 2),
        "sleep_score": sleep_score or None,
    }


def _classify_phase(bedtime: datetime, wake_time: datetime, tzinfo: ZoneInfo) -> tuple[str, str]:
    bedtime_local = bedtime.astimezone(tzinfo)
    wake_local = wake_time.astimezone(tzinfo)
    bedtime_hour = bedtime_local.hour + bedtime_local.minute / 60.0
    wake_hour = wake_local.hour + wake_local.minute / 60.0

    if bedtime_hour <= 23.5 and 6.0 <= wake_hour <= 8.5:
        return "Aligned", "Good Alignment"
    if bedtime_hour > 0.0 and bedtime_hour < 2.0:
        return "Delayed", "Sleep Window Shifted"
    if wake_hour < 5.5:
        return "Short", "Early Wake"
    return "Mixed", "Needs Rhythm Tuning"


def _empty_summary(tzinfo: ZoneInfo, range_value: str) -> dict[str, Any]:
    return {
        "sleep_score": None,
        "duration": 0.0,
        "efficiency": None,
        "stages": {"rem": 0.0, "deep": 0.0, "light": 0.0, "awake": 0.0},
        "hrv": None,
        "rhr": None,
        "recovery_score": None,
        "timeline_data": [],
        "weekly_data": [],
        "sleep_debt_hours": None,
        "target_sleep_hours": 8.0,
        "sleep_date": None,
        "sleep_date_label": None,
        "bedtime": None,
        "wake_time": None,
        "circadian_phase": "No data",
        "circadian_alignment": "No data available",
        "insights": [
            {"title": "No sleep data available", "detail": "Sync Google Fit or another wearable to populate this page.", "type": "info"},
        ],
        "recommendations": [
            {"title": "Connect a wearable", "detail": "Once sleep data lands in `user_vitals`, this view updates automatically.", "priority": "medium"},
        ],
        "data_sources": [],
        "status": "empty",
        "source": "db",
        "timezone": getattr(tzinfo, "key", "Asia/Kolkata"),
        "range": range_value,
        "empty": True,
    }


@dataclass
class SleepNightSample:
    night_key: str
    day_label: str
    source: str
    reference_end: datetime
    duration_hours: float
    sleep_score: int | None
    recorded_at: datetime
    has_explicit_score: bool


class SleepService:
    @staticmethod
    def _resolve_timezone(db: Session, user: User) -> ZoneInfo:
        connection = db.query(GoogleFitConnection).filter(GoogleFitConnection.user_id == user.id).first()
        candidate = (
            (connection.default_timezone if connection and connection.default_timezone else None)
            or settings.GOOGLE_FIT_DEFAULT_TIMEZONE
            or "Asia/Kolkata"
        )
        try:
            return ZoneInfo(candidate)
        except Exception:
            try:
                return ZoneInfo("Asia/Kolkata")
            except Exception:
                return timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")  # type: ignore[return-value]

    @staticmethod
    def _collect_sleep_samples(db: Session, user: User, tzinfo: ZoneInfo, lookback_days: int = 30) -> list[SleepNightSample]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        samples_by_night: dict[str, SleepNightSample] = {}

        def _sample_quality(sample: SleepNightSample) -> int:
            duration_score = 3 if sample.duration_hours > 0 else 0
            explicit_score = 2 if sample.has_explicit_score else 0
            source_score = 2 if sample.source == "user_vitals" else 1
            return duration_score + explicit_score + source_score

        vitals_rows = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.vital_type == UserVitalTypeEnum.SLEEP,
                UserVital.timestamp >= cutoff,
            )
            .order_by(UserVital.timestamp.desc())
            .all()
        )
        for row in vitals_rows:
            recorded_at = row.timestamp if row.timestamp.tzinfo else row.timestamp.replace(tzinfo=timezone.utc)
            duration_hours = _sleep_hours_from_user_vital(row) or 0.0
            unit = str(row.unit or "").strip().lower()
            reference_end = recorded_at if unit in {"minutes", "minute", "min", "mins"} else recorded_at + timedelta(hours=24)
            night_key = _night_key(reference_end, tzinfo)
            sample = SleepNightSample(
                night_key=night_key,
                day_label=_format_short_day(reference_end, tzinfo),
                source="user_vitals",
                reference_end=reference_end,
                duration_hours=duration_hours,
                sleep_score=None,
                recorded_at=recorded_at,
                has_explicit_score=False,
            )
            existing = samples_by_night.get(night_key)
            if not existing or existing.recorded_at <= sample.recorded_at:
                samples_by_night[night_key] = sample

        wearable_rows = (
            db.query(WearableData)
            .filter(
                WearableData.user_id == user.id,
                WearableData.recorded_at >= cutoff,
            )
            .order_by(WearableData.recorded_at.desc())
            .all()
        )
        for row in wearable_rows:
            if row.sleep_duration_minutes is None and row.sleep_score is None:
                continue
            recorded_at = row.recorded_at if row.recorded_at.tzinfo else row.recorded_at.replace(tzinfo=timezone.utc)
            reference_end = recorded_at + timedelta(hours=24)
            duration_hours = _safe_float(row.sleep_duration_minutes, 0.0) or 0.0
            duration_hours = duration_hours / 60.0 if duration_hours > 0 else 0.0
            sleep_score = _safe_int(row.sleep_score, None)
            night_key = _night_key(reference_end, tzinfo)
            sample = SleepNightSample(
                night_key=night_key,
                day_label=_format_short_day(reference_end, tzinfo),
                source="wearable_data",
                reference_end=reference_end,
                duration_hours=duration_hours,
                sleep_score=sleep_score,
                recorded_at=recorded_at,
                has_explicit_score=sleep_score is not None,
            )
            existing = samples_by_night.get(night_key)
            if not existing:
                samples_by_night[night_key] = sample
                continue

            existing_rank = _sample_quality(existing)
            sample_rank = _sample_quality(sample)
            if sample_rank > existing_rank or (sample_rank == existing_rank and sample.recorded_at >= existing.recorded_at):
                samples_by_night[night_key] = sample

        return sorted(samples_by_night.values(), key=lambda item: item.reference_end, reverse=True)

    @staticmethod
    def _collect_heart_samples(db: Session, user: User, window_start: datetime, window_end: datetime) -> list[float]:
        values: list[float] = []

        vitals_rows = (
            db.query(UserVital)
            .filter(
                UserVital.user_id == user.id,
                UserVital.vital_type == UserVitalTypeEnum.HEART_RATE,
                UserVital.timestamp >= window_start,
                UserVital.timestamp <= window_end,
            )
            .order_by(UserVital.timestamp.asc())
            .all()
        )
        for row in vitals_rows:
            if row.value is not None:
                values.append(float(row.value))

        legacy_rows = (
            db.query(VitalsData)
            .filter(
                VitalsData.user_id == user.id,
                VitalsData.recorded_at >= window_start,
                VitalsData.recorded_at <= window_end,
            )
            .order_by(VitalsData.recorded_at.asc())
            .all()
        )
        for row in legacy_rows:
            if row.heart_rate_bpm is not None:
                values.append(float(row.heart_rate_bpm))

        return values

    @staticmethod
    def _build_weekly_data(samples: list[SleepNightSample], history_days: int) -> list[dict[str, Any]]:
        weekly_rows = []
        for sample in samples[:history_days]:
            score = sample.sleep_score if sample.sleep_score is not None else _estimate_sleep_score(sample.duration_hours, None, None)
            weekly_rows.append(_build_weekly_row(
                {
                    "night_key": sample.night_key,
                    "day_label": sample.day_label,
                    "duration_hours": sample.duration_hours,
                    "sleep_score": score,
                }
            ))
        return list(reversed(weekly_rows))

    @staticmethod
    def get_sleep_score(db: Session, user: User) -> int | None:
        return SleepService.get_sleep_summary(db, user)["data"].get("sleep_score")

    @staticmethod
    def get_sleep_stages(db: Session, user: User) -> dict[str, float]:
        return SleepService.get_sleep_summary(db, user)["data"].get("stages", {})

    @staticmethod
    def get_recovery_metrics(db: Session, user: User) -> dict[str, Any]:
        payload = SleepService.get_sleep_summary(db, user)["data"]
        return {
            "hrv": payload.get("hrv"),
            "rhr": payload.get("rhr"),
            "recovery_score": payload.get("recovery_score"),
        }

    @staticmethod
    def get_sleep_summary(db: Session, user: User, range_value: str = "24h") -> dict[str, Any]:
        tzinfo = SleepService._resolve_timezone(db, user)
        range_value = range_value if range_value in SLEEP_HISTORY_RANGE_DAYS else "24h"
        history_days = SLEEP_HISTORY_RANGE_DAYS.get(range_value, 7)

        samples = SleepService._collect_sleep_samples(db, user, tzinfo, lookback_days=max(history_days, 30))
        if not samples:
            summary = _empty_summary(tzinfo, range_value)
            return {
                "success": True,
                "status": "fallback",
                "source": "db",
                "error": None,
                "data": summary,
                "last_updated": None,
            }

        latest = samples[0]
        duration_hours = round(float(latest.duration_hours or 0.0), 2)
        wake_time = latest.reference_end
        sleep_start = wake_time - timedelta(hours=max(duration_hours, 4.0))
        window_start = sleep_start - timedelta(minutes=30)
        window_end = wake_time + timedelta(minutes=30)

        heart_values = SleepService._collect_heart_samples(db, user, window_start, window_end)
        avg_hr = _mean(heart_values)
        hrv = _estimate_hrv_proxy(heart_values, duration_hours, latest.sleep_score or 75)
        rhr = _estimate_rhr(heart_values, duration_hours, latest.sleep_score or 75)

        sleep_score = latest.sleep_score if latest.sleep_score is not None else _estimate_sleep_score(duration_hours, hrv, rhr)
        stages = _sleep_stage_profile(duration_hours, float(sleep_score))
        efficiency = _estimate_efficiency(duration_hours, sleep_score, stages)
        recovery_score = _estimate_recovery_score(sleep_score, efficiency, hrv, rhr)
        timeline = _build_timeline(duration_hours, stages, sleep_start, wake_time)
        weekly = SleepService._build_weekly_data(samples, history_days)
        phase_label, alignment_label = _classify_phase(sleep_start, wake_time, tzinfo)
        sleep_debt = round(max(0.0, 8.0 - duration_hours), 1)

        insights: list[dict[str, str]] = []
        recommendations: list[dict[str, str]] = []

        if duration_hours < 7.0:
            insights.append(
                {
                    "title": "Sleep duration is light",
                    "detail": f"You logged {duration_hours:.1f}h last night, which is below the 8h target.",
                    "type": "warning",
                }
            )
            recommendations.append(
                {
                    "title": "Add more sleep opportunity",
                    "detail": f"Shift tonight's window earlier by about {sleep_debt:.1f}h if possible.",
                    "priority": "high",
                }
            )
        else:
            insights.append(
                {
                    "title": "Sleep duration is holding steady",
                    "detail": f"Last night's total sleep reached {duration_hours:.1f}h.",
                    "type": "success",
                }
            )

        if stages["awake"] >= 10.0:
            insights.append(
                {
                    "title": "Sleep was fragmented",
                    "detail": f"Awake time accounted for {stages['awake']:.0f}% of the sleep window.",
                    "type": "warning",
                }
            )
            recommendations.append(
                {
                    "title": "Reduce overnight disruptions",
                    "detail": "Cool the room, reduce late liquids, and avoid bright screens before bed.",
                    "priority": "medium",
                }
            )

        if rhr >= 60:
            insights.append(
                {
                    "title": "Resting heart rate stayed elevated",
                    "detail": f"Overnight RHR sat around {rhr} bpm, which can point to incomplete recovery.",
                    "type": "warning",
                }
            )
            recommendations.append(
                {
                    "title": "Finish training earlier",
                    "detail": "Try to end intense workouts at least 3 hours before bedtime.",
                    "priority": "medium",
                }
            )

        if hrv >= 60:
            insights.append(
                {
                    "title": "HRV recovery looks good",
                    "detail": f"Your overnight HRV proxy was {hrv} ms, signaling a stronger recovery window.",
                    "type": "success",
                }
            )
        else:
            insights.append(
                {
                    "title": "HRV is still modest",
                    "detail": f"Your overnight HRV proxy came in at {hrv} ms.",
                    "type": "info",
                }
            )

        if not recommendations:
            recommendations.append(
                {
                    "title": "Keep the current sleep routine",
                    "detail": "Your latest data does not show a major recovery bottleneck.",
                    "priority": "low",
                }
            )

        summary = {
            "sleep_score": sleep_score,
            "duration": duration_hours,
            "efficiency": efficiency,
            "stages": stages,
            "hrv": hrv,
            "rhr": rhr,
            "recovery_score": recovery_score,
            "timeline_data": timeline,
            "weekly_data": weekly,
            "sleep_debt_hours": sleep_debt,
            "target_sleep_hours": 8.0,
            "sleep_date": _format_date(wake_time, tzinfo),
            "sleep_date_label": wake_time.astimezone(tzinfo).strftime("%A, %b %d, %Y"),
            "bedtime": _format_time(sleep_start, tzinfo),
            "wake_time": _format_time(wake_time, tzinfo),
            "circadian_phase": phase_label,
            "circadian_alignment": alignment_label,
            "insights": insights,
            "recommendations": recommendations,
            "data_sources": [sample.source for sample in samples[: min(len(samples), 3)]],
            "avg_heart_rate": round(avg_hr, 1) if avg_hr is not None else None,
            "status": "ready",
            "source": "db",
            "timezone": getattr(tzinfo, "key", "Asia/Kolkata"),
            "range": range_value,
            "empty": False,
        }

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": summary,
            "last_updated": wake_time.isoformat(),
        }
