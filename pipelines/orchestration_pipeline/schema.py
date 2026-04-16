"""Orchestration pipeline DTOs."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OrchestrationPipelineRequest(BaseModel):
    user_id: str
    data_points: dict[str, Any] = Field(default_factory=dict)
    report_id: str | None = None


class OrchestrationPipelineResponse(BaseModel):
    success: bool = True
    status: str = "processing"
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
