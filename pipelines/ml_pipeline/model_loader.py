from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

import joblib

from pipelines.ml_pipeline.preprocess import FEATURE_NAMES
from pipelines.ml_pipeline.train import DEFAULT_MODEL_PATH, ensure_model_artifact


@dataclass
class LoadedModel:
    model: Any
    path: str
    version: str | None = None
    feature_names: tuple[str, ...] = FEATURE_NAMES
    label: str = "diabetes_risk"
    positive_class_index: int = 1
    training_summary: dict[str, Any] | None = None


class ModelLoader:
    _cached_model: LoadedModel | None = None
    _cached_path: str | None = None
    _lock = Lock()

    def __init__(self, model_path: str | None = None, *, auto_train_if_missing: bool = True):
        configured_path = (
            model_path
            or os.getenv("AI_INSIGHTS_MODEL_PATH")
            or os.getenv("ML_MODEL_PATH")
            or str(DEFAULT_MODEL_PATH)
        )
        self.model_path = configured_path.strip()
        self.auto_train_if_missing = auto_train_if_missing

    def resolve_path(self) -> Path:
        return Path(self.model_path).expanduser()

    def exists(self) -> bool:
        return bool(self.model_path) and self.resolve_path().is_file()

    def load(self) -> LoadedModel | None:
        path = self.resolve_path()
        if not path.is_file():
            if not self.auto_train_if_missing:
                return None
            ensure_model_artifact(path)

        resolved = str(path.resolve())
        with self._lock:
            if self._cached_model is not None and self._cached_path == resolved:
                return self._cached_model

            payload = joblib.load(path)
            loaded = self._deserialize(payload, path)
            self.__class__._cached_model = loaded
            self.__class__._cached_path = resolved
            return loaded

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
            feature_names = tuple(payload.get("feature_names") or FEATURE_NAMES)
            feature_names = ModelLoader._normalize_feature_names(payload["model"], feature_names)
            return LoadedModel(
                model=payload["model"],
                path=str(path),
                version=payload.get("model_version") or path.stem,
                feature_names=feature_names,
                label=str(payload.get("label") or "diabetes_risk"),
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
            positive_class_index=1,
            training_summary={},
        )
