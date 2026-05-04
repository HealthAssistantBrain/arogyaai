from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from models import Alert, AlertTypeEnum, Feedback, FeedbackEntityType, FeedbackType, Recommendation, RiskScore, User
from schemas.feedback import FeedbackCreate


class FeedbackEntityNotFoundError(ValueError):
    pass


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _normalize_entity_type(value: FeedbackEntityType | str) -> FeedbackEntityType:
    if isinstance(value, FeedbackEntityType):
        return value
    return FeedbackEntityType(str(value).strip().lower())


def _weighted_score(created_at: datetime | None) -> float:
    """Simple recency weight for downstream learning exports."""
    if created_at is None:
        return 1.0
    now = datetime.now(timezone.utc)
    observed = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    age_days = max((now - observed).days, 0)
    if age_days <= 7:
        return 1.5
    if age_days <= 30:
        return 1.2
    if age_days <= 90:
        return 1.0
    return 0.7


def _entity_exists(db: Session, user: User, entity_type: FeedbackEntityType, entity_id: UUID) -> bool:
    if entity_type == FeedbackEntityType.PREDICTION:
        return (
            db.query(RiskScore.id)
            .filter(RiskScore.id == entity_id, RiskScore.user_id == user.id)
            .first()
            is not None
        )

    if entity_type == FeedbackEntityType.EXPLANATION:
        return (
            db.query(RiskScore.id)
            .filter(RiskScore.id == entity_id, RiskScore.user_id == user.id)
            .first()
            is not None
        )

    if entity_type == FeedbackEntityType.RECOMMENDATION:
        return (
            db.query(Recommendation.id)
            .join(RiskScore, Recommendation.risk_score_id == RiskScore.id)
            .filter(Recommendation.id == entity_id, RiskScore.user_id == user.id)
            .first()
            is not None
        )

    if entity_type == FeedbackEntityType.ANOMALY:
        return (
            db.query(Alert.id)
            .filter(
                Alert.id == entity_id,
                Alert.user_id == user.id,
                Alert.alert_type == AlertTypeEnum.VITAL_ANOMALY,
            )
            .first()
            is not None
        )

    return False


def _serialize_feedback(record: Feedback) -> dict[str, Any]:
    metadata = record.feedback_metadata if isinstance(record.feedback_metadata, dict) else {}
    return {
        "id": record.id,
        "user_id": record.user_id,
        "entity_type": record.entity_type,
        "entity_id": record.entity_id,
        "rating": record.rating,
        "feedback_type": record.feedback_type,
        "comment": record.comment,
        "metadata": metadata,
        "created_at": record.created_at,
    }


def create_feedback(db: Session, user: User, payload: FeedbackCreate) -> dict[str, Any]:
    entity_type = _normalize_entity_type(payload.entity_type)
    if not _entity_exists(db, user, entity_type, payload.entity_id):
        raise FeedbackEntityNotFoundError(f"{entity_type.value} entity was not found for this user.")

    metadata = dict(payload.metadata or {})
    metadata["is_critical"] = bool(payload.is_critical)
    if payload.correction_before is not None:
        metadata["correction_before"] = payload.correction_before
    if payload.correction_after is not None:
        metadata["correction_after"] = payload.correction_after

    record = Feedback(
        user_id=user.id,
        entity_type=entity_type,
        entity_id=payload.entity_id,
        rating=payload.rating,
        feedback_type=payload.feedback_type,
        comment=payload.comment,
        feedback_metadata=metadata,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize_feedback(record)


def get_feedback_by_user(
    db: Session,
    user: User,
    *,
    entity_type: FeedbackEntityType | str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    query = db.query(Feedback).filter(Feedback.user_id == user.id)
    if entity_type is not None:
        query = query.filter(Feedback.entity_type == _normalize_entity_type(entity_type))
    rows = query.order_by(Feedback.created_at.desc()).offset(offset).limit(limit).all()
    return [_serialize_feedback(row) for row in rows]


def get_feedback_by_entity(
    db: Session,
    user: User,
    entity_id: UUID,
    *,
    entity_type: FeedbackEntityType | str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    query = db.query(Feedback).filter(Feedback.user_id == user.id, Feedback.entity_id == entity_id)
    if entity_type is not None:
        query = query.filter(Feedback.entity_type == _normalize_entity_type(entity_type))
    rows = query.order_by(Feedback.created_at.desc()).offset(offset).limit(limit).all()
    return [_serialize_feedback(row) for row in rows]


def aggregate_feedback_stats(
    db: Session,
    user: User | None = None,
    *,
    entity_type: FeedbackEntityType | str | None = None,
    entity_id: UUID | None = None,
) -> dict[str, Any]:
    query = db.query(Feedback)
    if user is not None:
        query = query.filter(Feedback.user_id == user.id)
    if entity_type is not None:
        query = query.filter(Feedback.entity_type == _normalize_entity_type(entity_type))
    if entity_id is not None:
        query = query.filter(Feedback.entity_id == entity_id)

    rows = query.all()
    ratings = [int(row.rating) for row in rows if row.rating is not None]
    by_type = Counter(_enum_value(row.feedback_type) for row in rows)
    by_entity_type = Counter(_enum_value(row.entity_type) for row in rows)

    return {
        "total": len(rows),
        "average_rating": round(sum(ratings) / len(ratings), 3) if ratings else None,
        "by_type": dict(by_type),
        "by_entity_type": dict(by_entity_type),
        "incorrect_prediction_rate": incorrect_prediction_rate(db, user=user),
        "explanation_helpfulness_score": explanation_helpfulness_score(db, user=user),
    }


def average_rating_per_model(db: Session, user: User | None = None) -> dict[str, float]:
    filters = [
        Feedback.entity_type.in_([FeedbackEntityType.PREDICTION, FeedbackEntityType.EXPLANATION]),
        Feedback.rating.isnot(None),
    ]
    if user is not None:
        filters.append(Feedback.user_id == user.id)

    rows = (
        db.query(RiskScore.model_version, func.avg(Feedback.rating))
        .join(RiskScore, Feedback.entity_id == RiskScore.id)
        .filter(and_(*filters))
        .group_by(RiskScore.model_version)
        .all()
    )
    return {str(model_version or "unknown"): round(float(avg_rating), 3) for model_version, avg_rating in rows}


def incorrect_prediction_rate(db: Session, user: User | None = None) -> float | None:
    query = db.query(Feedback).filter(
        Feedback.entity_type == FeedbackEntityType.PREDICTION,
        Feedback.feedback_type.in_(
            [FeedbackType.CORRECT, FeedbackType.INCORRECT, FeedbackType.PARTIAL]
        ),
    )
    if user is not None:
        query = query.filter(Feedback.user_id == user.id)

    rows = query.all()
    if not rows:
        return None
    incorrect = sum(1 for row in rows if row.feedback_type == FeedbackType.INCORRECT)
    return round(incorrect / len(rows), 4)


def explanation_helpfulness_score(db: Session, user: User | None = None) -> float | None:
    query = db.query(Feedback).filter(
        Feedback.entity_type == FeedbackEntityType.EXPLANATION,
        Feedback.feedback_type.in_([FeedbackType.HELPFUL, FeedbackType.NOT_HELPFUL]),
    )
    if user is not None:
        query = query.filter(Feedback.user_id == user.id)

    rows = query.all()
    if not rows:
        return None
    helpful = sum(1 for row in rows if row.feedback_type == FeedbackType.HELPFUL)
    return round(helpful / len(rows), 4)


def export_learning_events(
    db: Session,
    *,
    entity_type: FeedbackEntityType | str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    query = db.query(Feedback)
    if entity_type is not None:
        query = query.filter(Feedback.entity_type == _normalize_entity_type(entity_type))

    rows = query.order_by(Feedback.created_at.desc()).limit(limit).all()
    events: list[dict[str, Any]] = []
    for row in rows:
        metadata = row.feedback_metadata if isinstance(row.feedback_metadata, dict) else {}
        events.append(
            {
                "feedback_id": str(row.id),
                "user_id": str(row.user_id),
                "entity_type": _enum_value(row.entity_type),
                "entity_id": str(row.entity_id),
                "rating": row.rating,
                "feedback_type": _enum_value(row.feedback_type),
                "comment": row.comment,
                "metadata": metadata,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "learning_weight": _weighted_score(row.created_at),
                "is_critical": bool(metadata.get("is_critical")),
            }
        )
    return events


class FeedbackService:
    create_feedback = staticmethod(create_feedback)
    get_feedback_by_user = staticmethod(get_feedback_by_user)
    get_feedback_by_entity = staticmethod(get_feedback_by_entity)
    aggregate_feedback_stats = staticmethod(aggregate_feedback_stats)
    average_rating_per_model = staticmethod(average_rating_per_model)
    incorrect_prediction_rate = staticmethod(incorrect_prediction_rate)
    explanation_helpfulness_score = staticmethod(explanation_helpfulness_score)
    export_learning_events = staticmethod(export_learning_events)
