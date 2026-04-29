from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipelines.ml_pipeline.model_loader import LoadedModel
from pipelines.ml_pipeline.predict import predict_with_loaded_model
from pipelines.ml_pipeline.preprocess import FEATURE_NAMES, build_feature_vector

FEATURE_ORDER = FEATURE_NAMES


@dataclass
class InferenceResult:
    score: float
    risk_level: str
    confidence: float | None
    model_version: str | None
    raw_output: Any = None


class MLPipelineInference:
    def __init__(self, loaded_model: LoadedModel | None):
        self.loaded_model = loaded_model

    @property
    def available(self) -> bool:
        return self.loaded_model is not None

    def _vector(self, feature_payload: dict[str, Any]) -> list[float]:
        feature_names = self.loaded_model.feature_names if self.loaded_model is not None else None
        return build_feature_vector(feature_payload, feature_names)

    @staticmethod
    def _risk_level(probability: float) -> str:
        if probability >= 0.75:
            return "CRITICAL"
        if probability >= 0.50:
            return "HIGH"
        if probability >= 0.25:
            return "MODERATE"
        return "LOW"

    def predict(self, feature_payload: dict[str, Any]) -> InferenceResult | None:
        if self.loaded_model is None:
            return None

        vector = self._vector(feature_payload)
        try:
            prediction = predict_with_loaded_model(vector, self.loaded_model)
        except Exception:
            return None

        return InferenceResult(
            score=round(float(prediction.probability), 6),
            risk_level=self._risk_level(float(prediction.probability)),
            confidence=round(float(prediction.confidence), 6),
            model_version=prediction.model_version,
            raw_output=prediction.raw_output,
        )
