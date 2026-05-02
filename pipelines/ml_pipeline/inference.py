from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import warnings

import joblib
import numpy as np

from pipelines.ml_pipeline.model_loader import LoadedModel, ModelLoader
from pipelines.ml_pipeline.paths import DEFAULT_MODEL_PATH
from pipelines.ml_pipeline.preprocess import FEATURE_NAMES, MODEL_TYPES, build_feature_vector, normalize_model_type

FEATURE_ORDER = FEATURE_NAMES
RISK_OUTPUT_KEYS: dict[str, str] = {
    "diabetes": "diabetes_risk",
    "cardio": "cardio_risk",
    "sleep": "sleep_risk",
}


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
        if probability > 0.80:
            return "HIGH"
        if probability >= 0.50:
            return "MODERATE"
        return "LOW"

    def predict(self, feature_payload: dict[str, Any]) -> InferenceResult | None:
        if self.loaded_model is None:
            return None

        try:
            probability = predict(feature_payload, loaded_model=self.loaded_model)
        except Exception:
            return None

        return InferenceResult(
            score=round(float(probability), 6),
            risk_level=self._risk_level(float(probability)),
            confidence=round(float(probability), 6),
            model_version=self.loaded_model.version,
            raw_output={"probability": float(probability), "type": self.loaded_model.model_type},
        )

    @staticmethod
    def predict_all(feature_payload: dict[str, Any]) -> dict[str, float]:
        return predict_all(feature_payload)


def _load_artifact(model_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(model_path) if model_path is not None else DEFAULT_MODEL_PATH
    payload = joblib.load(path)
    if not isinstance(payload, dict) or "model" not in payload:
        return {"model": payload, "features": list(FEATURE_NAMES)}
    return payload


def _positive_class_probability(model: Any, probabilities: np.ndarray) -> float:
    classes = list(getattr(model, "classes_", []))
    if 1 in classes:
        return float(probabilities[0, classes.index(1)])
    if len(classes) == 1:
        return 1.0 if classes[0] == 1 else 0.0
    if probabilities.shape[1] > 1:
        return float(probabilities[0, 1])
    return float(probabilities[0, 0])


def _prediction_type_from_input(input_data: dict[str, Any], prediction_type: str | None) -> str:
    if prediction_type:
        return normalize_model_type(prediction_type)
    for key in ("prediction_type", "model_type", "type", "risk_type"):
        if key in input_data:
            return normalize_model_type(str(input_data.get(key)))
    return "diabetes"


def predict(
    input_data: dict[str, Any],
    *,
    model_path: str | Path | None = None,
    loaded_model: LoadedModel | None = None,
    prediction_type: str | None = None,
) -> float:
    if loaded_model is not None:
        model = loaded_model.model
        features = loaded_model.feature_names or FEATURE_NAMES
    else:
        resolved_type = _prediction_type_from_input(input_data, prediction_type)
        loaded = ModelLoader(
            model_path=str(model_path) if model_path is not None else None,
            model_type=resolved_type,
        ).load()
        if loaded is None:
            artifact = _load_artifact(model_path)
            model = artifact["model"]
            features = tuple(artifact.get("features") or artifact.get("feature_names") or FEATURE_NAMES)
        else:
            model = loaded.model
            features = loaded.feature_names or FEATURE_NAMES

    vector = np.asarray(build_feature_vector(input_data, features), dtype=float).reshape(1, -1)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="X does not have valid feature names.*")
        probabilities = np.asarray(model.predict_proba(vector), dtype=float)
    return float(np.clip(_positive_class_probability(model, probabilities), 0.0, 1.0))


def predict_all(input_data: dict[str, Any]) -> dict[str, float]:
    loaded_models = ModelLoader.load_all(strict=True)
    missing = [model_type for model_type in MODEL_TYPES if model_type not in loaded_models]
    if missing:
        raise RuntimeError(f"ML models could not be loaded for: {', '.join(missing)}")

    risks: dict[str, float] = {}
    for model_type in MODEL_TYPES:
        loaded_model = loaded_models[model_type]
        probability = predict(input_data, loaded_model=loaded_model)
        risks[RISK_OUTPUT_KEYS[model_type]] = round(float(probability), 6)
    return risks


predict_risks = predict_all
