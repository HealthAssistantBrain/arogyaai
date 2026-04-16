from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev
from typing import Any

from sqlalchemy.orm import Session

from models import User, UserVital, UserVitalTypeEnum, VitalsData, WearableData
from pipelines.storage_pipeline.service import StoragePipelineService


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(float(mean(values)), 2)


def _std_dev(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    return round(float(pstdev(values)), 2)


class BaselinePipelineService:
    @staticmethod
    def _series(db: Session, user: User, days: int, kind: str) -> list[float]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        values: list[float] = []

        if kind == "heart_rate":
            for row in (
                db.query(UserVital)
                .filter(
                    UserVital.user_id == user.id,
                    UserVital.vital_type == UserVitalTypeEnum.HEART_RATE,
                    UserVital.timestamp >= cutoff,
                )
                .all()
            ):
                if row.value is not None:
                    values.append(float(row.value))
            for row in (
                db.query(VitalsData)
                .filter(VitalsData.user_id == user.id, VitalsData.recorded_at >= cutoff)
                .all()
            ):
                if row.heart_rate_bpm is not None:
                    values.append(float(row.heart_rate_bpm))
            return values

        if kind == "steps":
            for row in (
                db.query(UserVital)
                .filter(
                    UserVital.user_id == user.id,
                    UserVital.vital_type == UserVitalTypeEnum.STEPS,
                    UserVital.timestamp >= cutoff,
                )
                .all()
            ):
                if row.value is not None:
                    values.append(float(row.value))
            for row in (
                db.query(WearableData)
                .filter(WearableData.user_id == user.id, WearableData.recorded_at >= cutoff)
                .all()
            ):
                if row.step_count is not None:
                    values.append(float(row.step_count))
            return values

        if kind == "sleep":
            for row in (
                db.query(UserVital)
                .filter(
                    UserVital.user_id == user.id,
                    UserVital.vital_type == UserVitalTypeEnum.SLEEP,
                    UserVital.timestamp >= cutoff,
                )
                .all()
            ):
                if row.value is not None:
                    values.append(float(row.value))
            for row in (
                db.query(WearableData)
                .filter(WearableData.user_id == user.id, WearableData.recorded_at >= cutoff)
                .all()
            ):
                if row.sleep_duration_minutes is not None:
                    values.append(float(row.sleep_duration_minutes) / 60.0)
            return values

        return values

    @staticmethod
    def compute_baselines(db: Session, user: User, feature_snapshot: Any | None = None) -> dict[str, Any]:
        metrics: list[dict[str, Any]] = []
        for metric_name in ("heart_rate", "steps", "sleep"):
            series_7d = BaselinePipelineService._series(db, user, 7, metric_name)
            series_30d = BaselinePipelineService._series(db, user, 30, metric_name)
            if not series_7d and not series_30d:
                continue

            metrics.append(
                {
                    "metric_name": f"{metric_name}_baseline",
                    "mean_7d": _mean(series_7d),
                    "mean_30d": _mean(series_30d),
                    "std_dev": _std_dev(series_30d),
                    "sample_count": len(series_30d),
                    "window_start": None,
                    "window_end": None,
                    "metric_payload": {
                        "metric_name": metric_name,
                        "feature_snapshot": feature_snapshot.to_dict() if hasattr(feature_snapshot, "to_dict") else feature_snapshot,
                    },
                }
            )

        persisted = StoragePipelineService.store_baseline_metrics(db, user, metrics)
        return {
            "success": True,
            "status": "ready",
            "source": "db+computed",
            "error": None,
            "data": {
                "metrics": [
                    {
                        "metric_name": item.metric_name,
                        "mean_7d": float(item.mean_7d) if item.mean_7d is not None else None,
                        "mean_30d": float(item.mean_30d) if item.mean_30d is not None else None,
                        "std_dev": float(item.std_dev) if item.std_dev is not None else None,
                        "sample_count": item.sample_count,
                        "calculated_at": item.calculated_at.isoformat() if item.calculated_at else None,
                    }
                    for item in persisted
                ]
            },
        }
