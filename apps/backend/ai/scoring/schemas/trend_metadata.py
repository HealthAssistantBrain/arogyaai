from __future__ import annotations

from pydantic import BaseModel, Field


class TrendMetadata(BaseModel):
    direction: str = Field(default="stable")
    slope: float = 0.0
    change_percent: float = 0.0
    window: str = "24h"
    consistency: float = 0.0
