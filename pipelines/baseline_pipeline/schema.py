"""Baseline pipeline DTOs."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BaselinePipelineRequest(BaseModel):
    user_id: str
    metric_names: list[str] = Field(default_factory=list)


class BaselinePipelineResponse(BaseModel):
    success: bool = True
    status: str = "ready"
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
