from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .synthetic_snapshot import SyntheticSnapshot


class LongitudinalSequence(BaseModel):
    user_id: str
    synthetic_profile: str
    demographic_profile: str
    records: list[SyntheticSnapshot] = Field(default_factory=list)
    state_points: list[dict[str, Any]] = Field(default_factory=list)
    trajectory_summary: dict[str, Any] = Field(default_factory=dict)
    feature_vectors: list[dict[str, Any]] = Field(default_factory=list)
    temporal_windows: list[dict[str, Any]] = Field(default_factory=list)
    playback: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
