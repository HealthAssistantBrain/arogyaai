from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from models import User, UserProfile, UserVital, UserVitalTypeEnum


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


class WearableSignalCollector:
    @staticmethod
    def collect(
        db: Session,
        user: User,
        *,
        feature_snapshot: Any | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
        rows = (
            db.query(UserVital)
            .filter(UserVital.user_id == user.id, UserVital.timestamp >= cutoff)
            .order_by(UserVital.timestamp.asc())
            .all()
        )
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

        histories: dict[str, list[float]] = defaultdict(list)
        timestamps: dict[str, datetime | None] = {}
        current: dict[str, float | int | None] = {}
        units: dict[str, str | None] = {}

        for row in rows:
            metric_name = str(getattr(row.vital_type, "value", row.vital_type))
            if row.value is None:
                continue
            value = float(row.value)
            histories[metric_name].append(value)
            timestamps[metric_name] = row.timestamp
            current[metric_name] = value
            units[metric_name] = row.unit

        def latest(metric_name: str, fallback: Any = None) -> Any:
            return current.get(metric_name, fallback)

        def average(metric_name: str, window: int = 7) -> float | None:
            values = histories.get(metric_name, [])
            if not values:
                return None
            window_values = values[-window:] if len(values) >= window else values
            return round(float(mean(window_values)), 3)

        snapshot_payload = (
            feature_snapshot.feature_payload
            if hasattr(feature_snapshot, "feature_payload") and isinstance(feature_snapshot.feature_payload, dict)
            else (
                feature_snapshot.to_dict()
                if hasattr(feature_snapshot, "to_dict")
                else (feature_snapshot if isinstance(feature_snapshot, dict) else {})
            )
        )
        snapshot_payload = snapshot_payload if isinstance(snapshot_payload, dict) else {}

        sleep_hours = latest("sleep")
        sleep_unit = units.get("sleep")
        if sleep_hours is not None and sleep_unit and sleep_unit.lower().startswith("min"):
            sleep_hours = sleep_hours / 60.0
        sleep_hours = sleep_hours if sleep_hours is not None else _safe_float(snapshot_payload.get("sleep_duration") or snapshot_payload.get("sleep"))

        current_payload = {
            "heart_rate": latest("heart_rate", _safe_float(snapshot_payload.get("heart_rate") or snapshot_payload.get("hr_mean_7d"))),
            "resting_hr": _safe_float(snapshot_payload.get("avg_rhr")) or average("heart_rate", 10),
            "hrv": _safe_float(snapshot_payload.get("avg_hrv")),
            "spo2": latest("spo2"),
            "glucose": latest("glucose", _safe_float(snapshot_payload.get("glucose"))),
            "sleep_hours": round(float(sleep_hours), 3) if sleep_hours is not None else None,
            "activity_steps": latest("steps", _safe_float(snapshot_payload.get("activity_level") or snapshot_payload.get("steps_avg_7d"))),
            "bmi": _safe_float(snapshot_payload.get("bmi")),
            "stress_level": _safe_float(snapshot_payload.get("stress") or getattr(profile, "stress_level", None)),
            "blood_pressure_systolic": latest("blood_pressure_systolic", _safe_float(snapshot_payload.get("systolic_bp"))),
            "blood_pressure_diastolic": latest("blood_pressure_diastolic", _safe_float(snapshot_payload.get("diastolic_bp"))),
            "sleep_efficiency": _safe_float(snapshot_payload.get("sleep_efficiency") or snapshot_payload.get("sleep_score")),
            "latest_observation_at": max(
                [value for value in timestamps.values() if value is not None],
                default=getattr(feature_snapshot, "latest_observation_at", None),
            ),
        }
        current_payload["fatigue_proxy"] = (
            (
                max(0.0, 7.5 - float(current_payload["sleep_hours"] or 7.5)) * 4.0
                + max(0.0, float(current_payload["resting_hr"] or 60.0) - 60.0) * 0.8
                + max(0.0, 45.0 - float(current_payload["hrv"] or 45.0)) * 0.4
            )
            if current_payload.get("sleep_hours") is not None or current_payload.get("resting_hr") is not None or current_payload.get("hrv") is not None
            else None
        )

        fatigue_history: list[float] = []
        sleep_history = histories.get("sleep", [])
        hr_history = histories.get("heart_rate", [])
        history_length = max(len(sleep_history), len(hr_history), 1)
        for index in range(history_length):
            sleep_value = sleep_history[index] / 60.0 if index < len(sleep_history) and sleep_unit and sleep_unit.lower().startswith("min") else (sleep_history[index] if index < len(sleep_history) else sleep_hours)
            hr_value = hr_history[index] if index < len(hr_history) else current_payload.get("resting_hr")
            fatigue_history.append(
                round(
                    max(0.0, 7.5 - float(sleep_value or 7.5)) * 4.0
                    + max(0.0, float(hr_value or 60.0) - 60.0) * 0.8,
                    3,
                )
            )
        histories["fatigue_proxy"] = fatigue_history

        return {
            "current": current_payload,
            "histories": {key: [float(value) for value in values] for key, values in histories.items()},
            "timestamps": timestamps,
            "source_coverage": {
                "wearable": bool(rows),
                "sleep": current_payload.get("sleep_hours") is not None,
                "cardio": current_payload.get("heart_rate") is not None or current_payload.get("resting_hr") is not None,
                "respiratory": current_payload.get("spo2") is not None,
                "metabolic": current_payload.get("glucose") is not None or current_payload.get("bmi") is not None,
            },
            "profile": {
                "age": getattr(profile, "age", None),
                "gender": getattr(profile, "gender", None),
                "height_cm": _safe_float(getattr(profile, "height_cm", None)),
                "weight_kg": _safe_float(getattr(profile, "weight_kg", None)),
                "sleep_hours": _safe_float(getattr(profile, "sleep_hours", None)),
                "stress_level": _safe_float(getattr(profile, "stress_level", None)),
            },
            "row_count": len(rows),
        }
