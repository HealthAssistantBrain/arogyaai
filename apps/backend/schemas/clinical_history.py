from __future__ import annotations

from pydantic import BaseModel, Field


class ClinicalHistoryCreate(BaseModel):
    chief_complaint: str | None = None
    duration_value: int | None = Field(default=None, ge=1, le=3650)
    duration_unit: str | None = None
    onset: str | None = None
    severity: int | None = Field(default=None, ge=1, le=10)
    associated_symptoms: list[str] = Field(default_factory=list)
    negative_symptoms: list[str] = Field(default_factory=list)
    aggravating_factors: str | None = None
    relieving_factors: str | None = None
    previous_episodes: bool | None = None
    treatment_taken: str | None = None
