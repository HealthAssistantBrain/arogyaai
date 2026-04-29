from __future__ import annotations

from threading import Lock
from typing import Any

import numpy as np
import shap

from pipelines.ml_pipeline.model_loader import LoadedModel, ModelLoader
from pipelines.ml_pipeline.preprocess import FEATURE_NAMES, build_feature_map, build_feature_vector
from pipelines.ml_pipeline.schemas import ShapFactor


class ShapExplainer:
    _explainer_cache: dict[str, shap.TreeExplainer] = {}
    _lock = Lock()

    @classmethod
    def _get_explainer(cls, loaded_model: LoadedModel) -> shap.TreeExplainer:
        cache_key = loaded_model.path
        with cls._lock:
            explainer = cls._explainer_cache.get(cache_key)
            if explainer is None:
                explainer = shap.TreeExplainer(loaded_model.model)
                cls._explainer_cache[cache_key] = explainer
        return explainer

    @staticmethod
    def _normalize_values(raw_values: Any, positive_class_index: int) -> np.ndarray:
        if isinstance(raw_values, list):
            return np.asarray(raw_values[positive_class_index][0], dtype=float)

        array = np.asarray(raw_values, dtype=float)
        if array.ndim == 3:
            return array[0, :, positive_class_index]
        if array.ndim == 2:
            return array[0]
        if array.ndim == 1:
            return array
        raise ValueError("Unsupported SHAP output shape.")

    @classmethod
    def explain(
        cls,
        snapshot: Any,
        *,
        loaded_model: LoadedModel | None = None,
        features: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        effective_model = loaded_model or ModelLoader().load()
        if effective_model is None:
            raise RuntimeError("ML model is not available for SHAP explainability.")

        feature_names = effective_model.feature_names or FEATURE_NAMES
        feature_vector = list(features) if features is not None else build_feature_vector(snapshot, feature_names)
        feature_map = build_feature_map(snapshot, feature_names)
        explainer = cls._get_explainer(effective_model)
        raw_values = explainer.shap_values(np.asarray([feature_vector], dtype=float), check_additivity=False)
        normalized = cls._normalize_values(raw_values, effective_model.positive_class_index)

        factors: list[dict[str, Any]] = []
        for feature_name, shap_value in zip(feature_names, normalized, strict=True):
            factor = ShapFactor(
                feature=feature_name,
                value=float(shap_value),
                direction="positive" if float(shap_value) >= 0 else "negative",
                feature_value=feature_map.get(feature_name),
            )
            factors.append(factor.as_storage())

        return factors
