from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FeedbackLearningEvent(BaseModel):
    feedback_id: str
    user_id: str
    entity_type: str
    entity_id: str
    rating: int | None = None
    feedback_type: str
    comment: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    learning_weight: float = 1.0
    is_critical: bool = False


class FeedbackLearningBatch(BaseModel):
    success: bool = True
    status: str = "ready"
    source: str = "feedback_pipeline"
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
