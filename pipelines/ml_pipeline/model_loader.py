from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

import joblib

from pipelines.ml_pipeline.preprocess import FEATURE_NAMES, MODEL_TYPES, normalize_model_type
from pipelines.ml_pipeline.paths import (
    DEFAULT_MODEL_PATH,
    DISEASE_MODEL_PATHS,
    LEGACY_DEFAULT_MODEL_PATH,
    LEGACY_DISEASE_MODEL_PATHS,
)


@dataclass
class LoadedModel:
    model: Any
    path: str
    version: str | None = None
    feature_names: tuple[str, ...] = FEATURE_NAMES
    label: str = "diabetes_risk"
    model_type: str = "diabetes"
    shap_model: Any | None = None
    shap_transformer: Any | None = None
    positive_class_index: int = 1
    training_summary: dict[str, Any] | None = None


class ModelLoader:
    _cached_models: dict[str, LoadedModel] = {}
    _lock = Lock()

    _TYPE_ENV_VARS: dict[str, tuple[str, ...]] = {
        "diabetes": ("ML_DIABETES_MODEL_PATH", "DIABETES_MODEL_PATH"),
        "cardio": ("ML_CARDIO_MODEL_PATH", "ML_CARDIOVASCULAR_MODEL_PATH", "CARDIO_MODEL_PATH"),
        "sleep": ("ML_SLEEP_MODEL_PATH", "SLEEP_MODEL_PATH"),
    }

    def __init__(
        self,
        model_path: str | None = None,
        *,
        auto_train_if_missing: bool = True,
        model_type: str | None = None,
        prediction_type: str | None = None,
    ):
        self.model_type = normalize_model_type(prediction_type or model_type)
        configured_path = self._configured_path(model_path, self.model_type)
        self.model_path = configured_path.strip()
        self.auto_train_if_missing = auto_train_if_missing

    @classmethod
    def _configured_path(cls, model_path: str | None, model_type: str) -> str:
        if model_path:
            return model_path

        for env_name in cls._TYPE_ENV_VARS[model_type]:
            configured = os.getenv(env_name)
            if configured:
                return configured

        if model_type == "diabetes":
            configured = os.getenv("AI_INSIGHTS_MODEL_PATH") or os.getenv("ML_MODEL_PATH")
            if configured:
                return configured

        primary_path = DISEASE_MODEL_PATHS[model_type]
        if primary_path.is_file():
            return str(primary_path)

        allow_legacy_fallback = os.getenv("ML_ALLOW_LEGACY_MODEL_FALLBACK", "").strip().lower() in {"1", "true", "yes"}
        legacy_path = LEGACY_DISEASE_MODEL_PATHS[model_type]
        if allow_legacy_fallback and legacy_path.is_file():
            return str(legacy_path)

        if allow_legacy_fallback and model_type == "diabetes" and LEGACY_DEFAULT_MODEL_PATH.is_file():
            return str(LEGACY_DEFAULT_MODEL_PATH)

        return str(primary_path)

    def resolve_path(self) -> Path:
        return Path(self.model_path).expanduser()

    def exists(self) -> bool:
        return bool(self.model_path) and self.resolve_path().is_file()

    def load(self) -> LoadedModel | None:
        path = self.resolve_path()
        if not path.is_file():
            if not self.auto_train_if_missing:
                return None
            from pipelines.ml_pipeline.train import ensure_model_artifact

            ensure_model_artifact(path, model_type=self.model_type)

        resolved = str(path.resolve())
        with self._lock:
            cached_model = self._cached_models.get(resolved)
            if cached_model is not None:
                return cached_model

            payload = joblib.load(path)
            loaded = self._deserialize(payload, path)
            self.__class__._cached_models[resolved] = loaded
            return loaded

    @classmethod
    def load_all(cls, *, auto_train_if_missing: bool = True, strict: bool = False) -> dict[str, LoadedModel]:
        loaded_models: dict[str, LoadedModel] = {}
        errors: dict[str, Exception] = {}
        for model_type in MODEL_TYPES:
            try:
                loaded_model = cls(auto_train_if_missing=auto_train_if_missing, model_type=model_type).load()
            except Exception as exc:
                errors[model_type] = exc
                loaded_model = None
            if loaded_model is not None:
                loaded_models[model_type] = loaded_model
        missing = [model_type for model_type in MODEL_TYPES if model_type not in loaded_models]
        if strict and (errors or missing):
            error_details = [f"{model_type}: {exc}" for model_type, exc in errors.items()]
            error_details.extend(f"{model_type}: not found" for model_type in missing if model_type not in errors)
            raise RuntimeError(f"ML models could not be loaded: {', '.join(error_details)}")
        return loaded_models

    @staticmethod
    def _expected_feature_count(model: Any) -> int | None:
        raw_count = getattr(model, "n_features_in_", None)
        try:
            return int(raw_count) if raw_count is not None else None
        except (TypeError, ValueError):
            return None

    @classmethod
    def _normalize_feature_names(cls, model: Any, feature_names: tuple[str, ...]) -> tuple[str, ...]:
        expected_count = cls._expected_feature_count(model)
        if expected_count is None or expected_count <= 0:
            return feature_names

        if len(feature_names) >= expected_count:
            return feature_names[:expected_count]
        return FEATURE_NAMES[:expected_count]

    @staticmethod
    def _deserialize(payload: Any, path: Path) -> LoadedModel:
        if isinstance(payload, dict) and "model" in payload:
            feature_names = tuple(payload.get("features") or payload.get("feature_names") or FEATURE_NAMES)
            feature_names = ModelLoader._normalize_feature_names(payload["model"], feature_names)
            model_type = normalize_model_type(
                payload.get("type")
                or payload.get("model_type")
                or payload.get("label")
            )
            return LoadedModel(
                model=payload["model"],
                path=str(path),
                version=payload.get("model_version") or payload.get("version") or path.stem,
                feature_names=feature_names,
                label=str(payload.get("label") or "diabetes_risk"),
                model_type=model_type,
                shap_model=payload.get("shap_model") or payload.get("base_model") or payload["model"],
                shap_transformer=payload.get("shap_transformer"),
                positive_class_index=int(payload.get("positive_class_index") or 1),
                training_summary=dict(payload.get("training_summary") or {}),
            )

        feature_names = ModelLoader._normalize_feature_names(payload, FEATURE_NAMES)
        return LoadedModel(
            model=payload,
            path=str(path),
            version=path.stem,
            feature_names=feature_names,
            label="diabetes_risk",
            model_type="diabetes",
            shap_model=payload,
            positive_class_index=1,
            training_summary={},
        )
