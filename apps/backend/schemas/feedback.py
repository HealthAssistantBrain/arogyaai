from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.feedback import FeedbackEntityType, FeedbackType


class FeedbackCreate(BaseModel):
    entity_type: FeedbackEntityType
    entity_id: UUID
    rating: int | None = Field(default=None, ge=1, le=5)
    feedback_type: FeedbackType
    comment: str | None = Field(default=None, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_critical: bool = False
    correction_before: dict[str, Any] | None = None
    correction_after: dict[str, Any] | None = None

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    entity_type: FeedbackEntityType
    entity_id: UUID
    rating: int | None = None
    feedback_type: FeedbackType
    comment: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class FeedbackListResponse(BaseModel):
    feedback: list[FeedbackResponse]
    count: int


class FeedbackStatsResponse(BaseModel):
    total: int
    average_rating: float | None = None
    by_type: dict[str, int] = Field(default_factory=dict)
    by_entity_type: dict[str, int] = Field(default_factory=dict)
    incorrect_prediction_rate: float | None = None
    explanation_helpfulness_score: float | None = None
