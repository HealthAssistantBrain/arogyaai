"""Lab pipeline DTOs."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LabPipelineRequest(BaseModel):
    user_id: str
    report_id: str | None = None
    text: str
    source_type: str = "PDF"
    source_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    page_metadata: list[dict[str, Any]] | None = None


class LabResultExtraction(BaseModel):
    test_name: str
    value: float
    unit: str | None = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    source_text: str | None = None
    source_span: str | None = None
    source_type: str = "PDF"
    page_number: int | None = None
    extraction_method: str = "structured_line"
    bbox: dict[str, Any] | None = None


class LabPipelineResponse(BaseModel):
    success: bool = True
    status: str = "ready"
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
