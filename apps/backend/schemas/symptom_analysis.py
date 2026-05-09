from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SymptomAnalysisCreate(BaseModel):
    chief_complaint: str = Field(min_length=3, max_length=1200)
    duration_value: int = Field(ge=1, le=3650)
    duration_unit: str = Field(min_length=3, max_length=16)
    severity: int = Field(ge=1, le=10)
    onset: str | None = Field(default=None, max_length=120)
    associated_symptoms: list[str] = Field(default_factory=list, min_length=1)
    aggravating_factors: str | None = Field(default=None, max_length=800)
    relieving_factors: str | None = Field(default=None, max_length=800)
    previous_episodes: str | None = Field(default=None, max_length=120)
    medications: str | None = Field(default=None, max_length=800)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("duration_unit")
    @classmethod
    def normalize_duration_unit(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        allowed = {"hour", "hours", "day", "days", "week", "weeks", "month", "months"}
        if normalized not in allowed:
            raise ValueError("duration_unit must be hours, days, weeks, or months")
        return normalized

    @field_validator("associated_symptoms")
    @classmethod
    def normalize_symptoms(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in value or []:
            text = str(item or "").strip()
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            cleaned.append(text)
        if not cleaned:
            raise ValueError("associated_symptoms must include at least one symptom")
        return cleaned


class SaveSymptomAnalysisToTimelineRequest(BaseModel):
    force: bool = False
