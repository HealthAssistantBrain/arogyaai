"""SHAP pipeline DTOs."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ShapPipelineRequest(BaseModel):
    prediction_id: str
    user_id: str
    risk_payload: dict[str, Any] = Field(default_factory=dict)


class ShapPipelineResponse(BaseModel):
    success: bool = True
    status: str = "ready"
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
