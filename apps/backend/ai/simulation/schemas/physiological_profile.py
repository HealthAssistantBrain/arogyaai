from __future__ import annotations

from pydantic import BaseModel, Field


class PhysiologicalProfile(BaseModel):
    user_id: str
    synthetic_profile: str
    demographic_profile: str
    age: int
    sex: str
    chronotype: str = "balanced"
    timezone: str = "UTC"
    baseline_metrics: dict[str, float] = Field(default_factory=dict)
    lifestyle_factors: dict[str, float | str | bool] = Field(default_factory=dict)
    behavior_traits: dict[str, float] = Field(default_factory=dict)
    disease_risks: dict[str, float] = Field(default_factory=dict)
    resilience: float = 0.5
    recovery_capacity: float = 0.5
    circadian_shift_hours: int = 0
    chronic_conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
