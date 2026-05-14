from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .dataset_contract import DatasetContract
from .longitudinal_sequence import LongitudinalSequence


class SimulationResult(BaseModel):
    run_id: str
    dataset_contract: DatasetContract
    sequences: list[LongitudinalSequence] = Field(default_factory=list)
    records: list[dict[str, Any]] = Field(default_factory=list)
    feature_vectors: list[dict[str, Any]] = Field(default_factory=list)
    temporal_windows: list[dict[str, Any]] = Field(default_factory=list)
    splits: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    manifests: dict[str, Any] = Field(default_factory=dict)
    exports: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    playback: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
