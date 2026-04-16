"""Lab pipeline DTOs."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LabPipelineRequest(BaseModel):
    user_id: str
    report_id: str | None = None
    text: str


class LabPipelineResponse(BaseModel):
    success: bool = True
    status: str = "ready"
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
