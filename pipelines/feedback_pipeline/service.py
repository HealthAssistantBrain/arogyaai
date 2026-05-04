from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models import FeedbackEntityType, User
from services.feedback_service import (
    aggregate_feedback_stats,
    average_rating_per_model,
    export_learning_events,
    explanation_helpfulness_score,
    incorrect_prediction_rate,
)


class FeedbackPipelineService:
    """Prepares feedback signals for ML retraining, RAG tuning, and anomaly tuning."""

    @staticmethod
    def collect_feedback_events(
        db: Session,
        *,
        entity_type: FeedbackEntityType | str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        return export_learning_events(db, entity_type=entity_type, limit=limit)

    @staticmethod
    def prepare_ml_retraining_data(db: Session, *, limit: int = 1000) -> list[dict[str, Any]]:
        events = export_learning_events(db, entity_type=FeedbackEntityType.PREDICTION, limit=limit)
        return [
            event
            for event in events
            if event["feedback_type"] in {"correct", "incorrect", "partial"} or event.get("rating") is not None
        ]

    @staticmethod
    def prepare_rag_tuning_data(db: Session, *, limit: int = 1000) -> list[dict[str, Any]]:
        events = export_learning_events(db, entity_type=FeedbackEntityType.EXPLANATION, limit=limit)
        return [
            event
            for event in events
            if event["feedback_type"] in {"helpful", "not_helpful", "partial"} or event.get("comment")
        ]

    @staticmethod
    def prepare_recommendation_tuning_data(db: Session, *, limit: int = 1000) -> list[dict[str, Any]]:
        events = export_learning_events(db, entity_type=FeedbackEntityType.RECOMMENDATION, limit=limit)
        return [
            event
            for event in events
            if event["feedback_type"] in {"helpful", "not_helpful", "partial"} or event.get("rating") is not None
        ]

    @staticmethod
    def prepare_anomaly_tuning_data(db: Session, *, limit: int = 1000) -> list[dict[str, Any]]:
        events = export_learning_events(db, entity_type=FeedbackEntityType.ANOMALY, limit=limit)
        return [
            event
            for event in events
            if event["feedback_type"] in {"correct", "incorrect", "partial"} or event.get("is_critical")
        ]

    @staticmethod
    def feedback_analytics(db: Session, user: User | None = None) -> dict[str, Any]:
        return {
            "stats": aggregate_feedback_stats(db, user=user),
            "average_rating_per_model": average_rating_per_model(db, user=user),
            "incorrect_prediction_rate": incorrect_prediction_rate(db, user=user),
            "explanation_helpfulness_score": explanation_helpfulness_score(db, user=user),
        }
