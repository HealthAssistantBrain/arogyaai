from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..utils import utc_now


class PreventiveAlert(BaseModel):
    alert_id: str
    title: str
    message: str
    severity: str = "info"
    domain: str = "general"
    escalation_level: str = "monitor"
    notification_class: str = "digest"
    rationale: list[str] = Field(default_factory=list)
    guidance: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
