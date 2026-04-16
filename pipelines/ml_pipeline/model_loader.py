from __future__ import annotations

import os
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LoadedModel:
    model: Any
    path: str
    version: str | None = None


class ModelLoader:
    """Loads future ML artifacts when they exist.

    The loader is deliberately conservative: if no artifact exists, callers get
    `None` and the pipeline continues through the safe rule-engine fallback.
    """

    def __init__(self, model_path: str | None = None):
        self.model_path = (model_path or os.getenv("AI_INSIGHTS_MODEL_PATH") or os.getenv("ML_MODEL_PATH") or "").strip()

    def exists(self) -> bool:
        return bool(self.model_path) and Path(self.model_path).expanduser().is_file()

    def load(self) -> LoadedModel | None:
        if not self.exists():
            return None

        path = Path(self.model_path).expanduser()
        with path.open("rb") as handle:
            model = pickle.load(handle)

        return LoadedModel(
            model=model,
            path=str(path),
            version=path.stem,
        )
