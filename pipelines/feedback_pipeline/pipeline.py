from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from pipelines.feedback_pipeline.schema import FeedbackLearningBatch
from pipelines.feedback_pipeline.service import FeedbackPipelineService


def run_feedback_pipeline(db: Session, *, limit: int = 1000) -> dict[str, Any]:
    try:
        payload = {
            "events": FeedbackPipelineService.collect_feedback_events(db, limit=limit),
            "ml_retraining": FeedbackPipelineService.prepare_ml_retraining_data(db, limit=limit),
            "rag_tuning": FeedbackPipelineService.prepare_rag_tuning_data(db, limit=limit),
            "recommendation_tuning": FeedbackPipelineService.prepare_recommendation_tuning_data(db, limit=limit),
            "anomaly_tuning": FeedbackPipelineService.prepare_anomaly_tuning_data(db, limit=limit),
            "analytics": FeedbackPipelineService.feedback_analytics(db),
        }
        return FeedbackLearningBatch(data=payload).model_dump()
    except Exception as exc:
        return FeedbackLearningBatch(
            success=False,
            status="failed",
            error=str(exc),
            data={
                "events": [],
                "ml_retraining": [],
                "rag_tuning": [],
                "recommendation_tuning": [],
                "anomaly_tuning": [],
            },
        ).model_dump()
