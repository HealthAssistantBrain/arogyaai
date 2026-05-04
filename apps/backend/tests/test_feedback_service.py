from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

from models import FeedbackEntityType, FeedbackType
from schemas.feedback import FeedbackCreate
from services import feedback_service


def test_create_feedback_persists_structured_learning_metadata():
    db = MagicMock()
    user = SimpleNamespace(id=uuid4())
    entity_id = uuid4()
    payload = FeedbackCreate(
        entity_type=FeedbackEntityType.PREDICTION,
        entity_id=entity_id,
        rating=2,
        feedback_type=FeedbackType.INCORRECT,
        comment="Risk level should be lower",
        metadata={"model_version": "cardio-v2"},
        is_critical=True,
        correction_before={"risk_level": "HIGH"},
        correction_after={"risk_level": "MODERATE"},
    )

    with patch.object(feedback_service, "_entity_exists", return_value=True):
        result = feedback_service.create_feedback(db, user, payload)

    stored = db.add.call_args.args[0]
    assert stored.user_id == user.id
    assert stored.entity_type == FeedbackEntityType.PREDICTION
    assert stored.entity_id == entity_id
    assert stored.rating == 2
    assert stored.feedback_type == FeedbackType.INCORRECT
    assert stored.feedback_metadata["model_version"] == "cardio-v2"
    assert stored.feedback_metadata["is_critical"] is True
    assert stored.feedback_metadata["correction_before"]["risk_level"] == "HIGH"
    assert result["metadata"]["correction_after"]["risk_level"] == "MODERATE"
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(stored)


def test_aggregate_feedback_stats_counts_feedback_categories():
    user = SimpleNamespace(id=uuid4())
    rows = [
        SimpleNamespace(
            rating=5,
            feedback_type=FeedbackType.CORRECT,
            entity_type=FeedbackEntityType.PREDICTION,
        ),
        SimpleNamespace(
            rating=1,
            feedback_type=FeedbackType.INCORRECT,
            entity_type=FeedbackEntityType.PREDICTION,
        ),
        SimpleNamespace(
            rating=4,
            feedback_type=FeedbackType.HELPFUL,
            entity_type=FeedbackEntityType.EXPLANATION,
        ),
    ]
    query = MagicMock()
    query.filter.return_value = query
    query.all.return_value = rows
    db = MagicMock()
    db.query.return_value = query

    with patch.object(feedback_service, "incorrect_prediction_rate", return_value=0.5), patch.object(
        feedback_service,
        "explanation_helpfulness_score",
        return_value=1.0,
    ):
        stats = feedback_service.aggregate_feedback_stats(db, user)

    assert stats["total"] == 3
    assert stats["average_rating"] == 3.333
    assert stats["by_type"]["incorrect"] == 1
    assert stats["by_entity_type"]["prediction"] == 2
    assert stats["incorrect_prediction_rate"] == 0.5
    assert stats["explanation_helpfulness_score"] == 1.0
