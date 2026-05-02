from __future__ import annotations

from collections.abc import Sequence
import warnings

from pipelines.ml_pipeline.model_loader import LoadedModel, ModelLoader
from pipelines.ml_pipeline.preprocess import SAFE_DEFAULTS
from pipelines.ml_pipeline.schemas import PredictionResult


def _normalize_features(loaded_model: LoadedModel, features: Sequence[float]) -> list[float]:
    normalized = list(features)
    expected_count = getattr(loaded_model.model, "n_features_in_", None)
    try:
        expected_count = int(expected_count) if expected_count is not None else None
    except (TypeError, ValueError):
        expected_count = None

    if expected_count is None or expected_count <= 0:
        expected_count = len(loaded_model.feature_names)

    if len(normalized) < expected_count:
        for feature_name in loaded_model.feature_names[len(normalized) : expected_count]:
            normalized.append(SAFE_DEFAULTS.get(feature_name, 0.0))

    return normalized[:expected_count]


def _predict_probability(loaded_model: LoadedModel, features: Sequence[float]) -> tuple[float, float, object]:
    normalized_features = _normalize_features(loaded_model, features)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="X does not have valid feature names.*")
        probabilities = loaded_model.model.predict_proba([normalized_features])[0]
    classes = list(getattr(loaded_model.model, "classes_", []))
    if 1 in classes:
        positive_index = classes.index(1)
    elif len(classes) == 1:
        probability = 1.0 if classes[0] == 1 else 0.0
        return probability, 1.0, probabilities
    elif loaded_model.positive_class_index < len(probabilities):
        positive_index = loaded_model.positive_class_index
    else:
        positive_index = 0
    probability = float(probabilities[positive_index])
    confidence = float(max(probabilities))
    return probability, confidence, probabilities


def predict_risk(features: Sequence[float], prediction_type: str | None = None) -> float:
    loaded_model = ModelLoader(model_type=prediction_type).load()
    if loaded_model is None:
        raise RuntimeError("ML model is not available for prediction.")
    probability, _, _ = _predict_probability(loaded_model, features)
    return float(probability)


def predict_with_loaded_model(
    features: Sequence[float],
    loaded_model: LoadedModel | None = None,
    prediction_type: str | None = None,
) -> PredictionResult:
    effective_model = loaded_model or ModelLoader(model_type=prediction_type).load()
    if effective_model is None:
        raise RuntimeError("ML model is not available for prediction.")

    probability, confidence, raw_output = _predict_probability(effective_model, features)
    return PredictionResult(
        probability=float(probability),
        confidence=float(confidence),
        model_version=effective_model.version,
        raw_output=raw_output,
    )
