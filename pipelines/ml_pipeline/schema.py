"""Contract objects for the ML pipeline."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MLPipelineRequest(BaseModel):
    user_id: str
    data_points: dict[str, Any] = Field(default_factory=dict)
    report_id: str | None = None


class MLPipelineResponse(BaseModel):
    success: bool = True
    status: str = "ready"
    source: str = "rule_engine"
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
