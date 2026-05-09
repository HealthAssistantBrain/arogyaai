from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ReportGenerationRequest(BaseModel):
    title: str | None = Field(default=None, max_length=180)
    report_ids: list[str] = Field(default_factory=list)
    symptom_session_ids: list[str] = Field(default_factory=list)
    timeline_start: str | None = None
    timeline_end: str | None = None
    include_wearables: bool = True
    include_biomarkers: bool = True
    include_timeline_events: bool = True

    @field_validator("report_ids", "symptom_session_ids")
    @classmethod
    def dedupe_ids(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in value or []:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            cleaned.append(text)
        return cleaned
