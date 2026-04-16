"""Feature pipeline DTOs."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FeaturePipelineRequest(BaseModel):
    user_id: str
    overrides: dict[str, Any] = Field(default_factory=dict)
    report_id: str | None = None


class FeaturePipelineResponse(BaseModel):
    success: bool = True
    status: str = "ready"
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
