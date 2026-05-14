from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DatasetContract(BaseModel):
    dataset_version: str
    schema_version: str
    generator_version: str
    generated_at: str
    sequence_window: dict[str, Any] = Field(default_factory=dict)
    feature_manifest: list[dict[str, Any]] = Field(default_factory=list)
    label_manifest: list[dict[str, Any]] = Field(default_factory=list)
    sequence_definitions: dict[str, Any] = Field(default_factory=dict)
    normalization_metadata: dict[str, Any] = Field(default_factory=dict)
    temporal_window_definitions: dict[str, Any] = Field(default_factory=dict)
    universal_schema_fields: list[str] = Field(
        default_factory=lambda: [
            "user_id",
            "timestamp",
            "signal_type",
            "signal_name",
            "value",
            "unit",
            "confidence",
            "baseline_delta",
            "anomaly_score",
            "risk_level",
            "physiological_state",
            "recovery_state",
            "trend_direction",
            "synthetic_profile",
            "demographic_profile",
            "trajectory_phase",
            "source",
            "labels",
            "metadata",
        ]
    )
