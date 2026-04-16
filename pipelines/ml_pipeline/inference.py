from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from pipelines.ml_pipeline.model_loader import LoadedModel


FEATURE_ORDER: Sequence[str] = (
    "hr_mean_7d",
    "steps_avg_7d",
    "sleep_efficiency",
    "bmi",
    "avg_hrv",
    "avg_rhr",
    "sleep_score",
    "sleep_duration",
    "activity_level",
    "systolic_bp",
    "diastolic_bp",
    "age",
    "cholesterol_proxy",
)


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
        vector: list[float] = []
        for key in FEATURE_ORDER:
            value = feature_payload.get(key)
            try:
                vector.append(float(value))
            except (TypeError, ValueError):
                vector.append(0.0)
        return vector

    def predict(self, feature_payload: dict[str, Any]) -> InferenceResult | None:
        if self.loaded_model is None:
            return None

        model = self.loaded_model.model
        vector = self._vector(feature_payload)
        raw_output: Any = None
        score = 0.0
        confidence = None

        try:
            if hasattr(model, "predict_proba"):
                raw_output = model.predict_proba([vector])
                if raw_output is not None and len(raw_output) > 0:
                    row = raw_output[0]
                    if hasattr(row, "__iter__") and len(row) > 1:
                        score = float(row[1]) * 100.0
                        confidence = float(row[1]) * 100.0
                    else:
                        score = float(row[0]) * 100.0
                        confidence = score
            elif hasattr(model, "predict"):
                raw_output = model.predict([vector])
                value = raw_output[0] if raw_output else 0.0
                score = float(value)
                if 0.0 <= score <= 1.0:
                    score *= 100.0
                confidence = min(100.0, max(0.0, score))
            else:
                return None
        except Exception:
            return None

        risk_level = "LOW"
        if score >= 65:
            risk_level = "CRITICAL"
        elif score >= 45:
            risk_level = "HIGH"
        elif score >= 25:
            risk_level = "MODERATE"

        return InferenceResult(
            score=round(min(max(score, 0.0), 100.0), 2),
            risk_level=risk_level,
            confidence=round(confidence, 2) if confidence is not None else None,
            model_version=self.loaded_model.version,
            raw_output=raw_output,
        )
