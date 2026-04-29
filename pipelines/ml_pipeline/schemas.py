from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


@dataclass(slots=True)
class PredictionResult:
    probability: float
    confidence: float
    model_version: str | None
    raw_output: Any = None


@dataclass(slots=True)
class ShapFactor:
    feature: str
    value: float
    direction: str
    feature_value: float | None = None

    def as_response(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "value": float(self.value),
            "direction": self.direction,
            "feature_value": None if self.feature_value is None else float(self.feature_value),
        }

    def as_storage(self) -> dict[str, Any]:
        payload = self.as_response()
        payload["feature_name"] = self.feature
        payload["shap_value"] = float(self.value)
        payload["explanation"] = f"{self.feature} has a {self.direction} contribution to the prediction."
        return payload


class MLPipelineRequest(BaseModel):
    user_id: str
    data_points: dict[str, Any] = Field(default_factory=dict)
    report_id: str | None = None


class MLPipelineResponse(BaseModel):
    success: bool = True
    status: str = "ready"
    source: str = "ml"
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


@dataclass(slots=True)
class ModelMetadata:
    feature_names: tuple[str, ...]
    model_version: str
    label: str = "diabetes_risk"
    positive_class_index: int = 1
    training_summary: dict[str, Any] = field(default_factory=dict)
