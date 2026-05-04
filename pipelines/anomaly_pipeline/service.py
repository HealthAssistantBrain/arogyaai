from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from models import User, UserVital, UserVitalTypeEnum
from pipelines.anomaly_pipeline.schema import AnomalySignal
from pipelines.anomaly_pipeline.utils import clean_floats, robust_z_score


_METRIC_LABELS = {
    "heart_rate": "heart rate",
    "steps": "step count",
    "sleep": "sleep duration",
    "spo2": "blood oxygen",
    "blood_pressure_systolic": "systolic blood pressure",
    "blood_pressure_diastolic": "diastolic blood pressure",
    "body_temperature": "body temperature",
    "calories_burned": "calories burned",
}


def _coerce_vital_type(value: Any) -> UserVitalTypeEnum | None:
    if isinstance(value, UserVitalTypeEnum):
        return value
    try:
        return UserVitalTypeEnum(str(value).strip().lower())
    except Exception:
        return None


def _metric_name(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value or "")


def _severity(metric: str, value: float, robust_z: float) -> str:
    if abs(robust_z) >= 5.0:
        return "critical"
    if metric == "heart_rate" and value >= 120.0:
        return "critical"
    if metric == "spo2" and value < 90.0:
        return "critical"
    if metric == "sleep" and value < 180.0:
        return "critical"
    return "warning"


def _message(metric: str, value: float, unit: str | None, baseline: float, direction: str) -> tuple[str, str]:
    label = _METRIC_LABELS.get(metric, metric.replace("_", " "))
    unit_label = f" {unit}" if unit else ""
    title = f"Unusual {label} pattern detected"
    message = (
        f"Latest {label} was {value:.1f}{unit_label}, "
        f"{direction} than the recent baseline of {baseline:.1f}{unit_label}."
    )
    return title, message


class AnomalyPipelineService:
    """Robust-baseline anomaly detector for wearable vitals.

    This is intentionally dependency-light. It can later be swapped for an
    Isolation Forest implementation without changing the service contract.
    """

    @staticmethod
    def detect_recent_vital_anomalies(
        db: Session,
        user: User,
        *,
        vital_types: list[str | UserVitalTypeEnum] | None = None,
        lookback_days: int = 30,
        min_points: int = 6,
        threshold: float = 3.5,
    ) -> list[dict[str, Any]]:
        user_id = getattr(user, "id", user)
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        allowed_types = [_coerce_vital_type(item) for item in vital_types or []]
        allowed_types = [item for item in allowed_types if item is not None]

        query = db.query(UserVital).filter(
            UserVital.user_id == user_id,
            UserVital.timestamp >= cutoff,
        )
        if allowed_types:
            query = query.filter(UserVital.vital_type.in_(allowed_types))

        rows = query.order_by(UserVital.vital_type.asc(), UserVital.timestamp.asc()).all()
        series: dict[str, list[UserVital]] = defaultdict(list)
        for row in list(rows or []):
            metric = _metric_name(getattr(row, "vital_type", None))
            if metric:
                series[metric].append(row)

        signals: list[AnomalySignal] = []
        for metric, metric_rows in series.items():
            if len(metric_rows) < min_points:
                continue

            latest = metric_rows[-1]
            values = clean_floats(getattr(row, "value", None) for row in metric_rows)
            if len(values) < min_points:
                continue

            latest_value = values[-1]
            history = values[:-1] or values
            robust_z, baseline = robust_z_score(latest_value, history)

            step_drop = metric == "steps" and baseline >= 1000.0 and latest_value < baseline * 0.4
            if abs(robust_z) < threshold and not step_drop:
                continue

            direction = "higher" if latest_value >= baseline else "lower"
            unit = getattr(latest, "unit", None)
            title, message = _message(metric, latest_value, unit, baseline, direction)
            signals.append(
                AnomalySignal(
                    metric=metric,
                    value=latest_value,
                    baseline=baseline,
                    robust_z_score=round(robust_z, 3),
                    direction=direction,
                    severity=_severity(metric, latest_value, robust_z),
                    title=title,
                    message=message,
                    observed_at=getattr(latest, "timestamp", None),
                    metadata={
                        "sample_count": len(values),
                        "lookback_days": lookback_days,
                        "threshold": threshold,
                        "detector": "median_mad",
                    },
                )
            )

        return [signal.model_dump() for signal in signals]
