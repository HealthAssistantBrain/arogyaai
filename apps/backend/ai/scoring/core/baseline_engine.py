from __future__ import annotations

import logging
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any

from sqlalchemy.orm import Session

from pipelines.schemas import BaselineMetricDTO
from pipelines.storage_pipeline.service import StoragePipelineService

from ..models.baseline_profile import BaselineMetricProfile, BaselineProfile

logger = logging.getLogger(__name__)


def _metric_profile(metric_name: str, values: list[float], generated_at: datetime) -> BaselineMetricProfile:
    cleaned = [float(value) for value in values if value is not None]
    mean_7d = float(mean(cleaned[-7:])) if cleaned else None
    mean_30d = float(mean(cleaned[-30:])) if cleaned else None
    std_dev = float(pstdev(cleaned)) if len(cleaned) >= 2 else 0.0
    return BaselineMetricProfile(
        metric_name=metric_name,
        mean_7d=round(mean_7d, 4) if mean_7d is not None else None,
        mean_30d=round(mean_30d, 4) if mean_30d is not None else None,
        std_dev=round(std_dev, 4) if std_dev is not None else None,
        sample_count=len(cleaned),
        window_start=generated_at,
        window_end=generated_at,
        payload={"source": "scoring_engine"},
    )


class BaselineEngine:
    @staticmethod
    def build_from_histories(
        *,
        user_id: str,
        histories: dict[str, list[float]],
        existing_rows: list[Any] | None = None,
    ) -> BaselineProfile:
        generated_at = datetime.now(timezone.utc)
        existing_map = {
            str(row.metric_name): BaselineMetricProfile(
                metric_name=str(row.metric_name),
                mean_7d=float(row.mean_7d) if row.mean_7d is not None else None,
                mean_30d=float(row.mean_30d) if row.mean_30d is not None else None,
                std_dev=float(row.std_dev) if row.std_dev is not None else None,
                sample_count=int(row.sample_count or 0),
                window_start=row.window_start,
                window_end=row.window_end,
                payload=row.metric_payload if isinstance(row.metric_payload, dict) else {},
            )
            for row in (existing_rows or [])
        }
        metrics = dict(existing_map)
        for metric_name, values in histories.items():
            cleaned = [float(value) for value in values if value is not None]
            if cleaned:
                metrics[metric_name] = _metric_profile(metric_name, cleaned, generated_at)
        return BaselineProfile(user_id=user_id, generated_at=generated_at, metrics=metrics)

    @staticmethod
    def persist(
        db: Session,
        user: Any,
        profile: BaselineProfile,
        *,
        extra_metrics: dict[str, float] | None = None,
    ) -> BaselineProfile:
        generated_at = profile.generated_at
        metrics = dict(profile.metrics)
        for metric_name, value in (extra_metrics or {}).items():
            metrics[metric_name] = BaselineMetricProfile(
                metric_name=metric_name,
                mean_7d=round(float(value), 4),
                mean_30d=round(float(value), 4),
                std_dev=0.0,
                sample_count=max(1, metrics.get(metric_name).sample_count if metrics.get(metric_name) else 1),
                window_start=generated_at,
                window_end=generated_at,
                payload={"source": "scoring_engine", "synthetic": True},
            )

        dtos = [
            BaselineMetricDTO.model_validate(
                {
                    "user_id": user.id,
                    "metric_name": metric.metric_name,
                    "mean_7d": metric.mean_7d,
                    "mean_30d": metric.mean_30d,
                    "std_dev": metric.std_dev,
                    "sample_count": metric.sample_count,
                    "window_start": metric.window_start,
                    "window_end": metric.window_end,
                    "metric_payload": metric.payload,
                }
            )
            for metric in metrics.values()
            if metric.sample_count > 0 or metric.reference is not None
        ]
        if dtos:
            StoragePipelineService.store_baseline_metrics(db, user, dtos)
            logger.info("[BASELINE UPDATED] user=%s metrics=%s", user.id, len(dtos))
        return BaselineProfile(user_id=profile.user_id, generated_at=generated_at, metrics=metrics)
