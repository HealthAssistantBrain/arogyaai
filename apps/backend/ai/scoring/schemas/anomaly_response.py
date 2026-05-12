from __future__ import annotations

from pydantic import BaseModel, Field


class AnomalyResponse(BaseModel):
    type: str
    severity: str
    metric: str
    message: str
    value: float | None = None
    baseline: float | None = None
    z_score: float | None = None
    timestamp: str | None = None
    metadata: dict[str, float | str | int | None] = Field(default_factory=dict)
