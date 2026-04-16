"""Storage pipeline DTOs."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StoragePipelineRequest(BaseModel):
    user_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class StoragePipelineResponse(BaseModel):
    success: bool = True
    status: str = "ready"
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
