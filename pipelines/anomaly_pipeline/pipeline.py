from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models import User
from pipelines.anomaly_pipeline.schema import AnomalyDetectionResponse
from pipelines.anomaly_pipeline.service import AnomalyPipelineService


def run_anomaly_pipeline(
    db: Session,
    user: User,
    *,
    vital_types: list[str] | None = None,
    lookback_days: int = 30,
    min_points: int = 6,
) -> dict[str, Any]:
    try:
        signals = AnomalyPipelineService.detect_recent_vital_anomalies(
            db,
            user,
            vital_types=vital_types,
            lookback_days=lookback_days,
            min_points=min_points,
        )
        return AnomalyDetectionResponse(data={"signals": signals}).model_dump()
    except Exception as exc:
        return AnomalyDetectionResponse(
            success=False,
            status="failed",
            error=str(exc),
            data={"signals": []},
        ).model_dump()
