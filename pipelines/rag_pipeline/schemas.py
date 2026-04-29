from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ShapSignal:
    feature_name: str
    display_name: str
    shap_value: float
    abs_shap_value: float
    direction: str
    feature_value: float | None = None
    category: str = "general"
    search_hint: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "display_name": self.display_name,
            "shap_value": float(self.shap_value),
            "abs_shap_value": float(self.abs_shap_value),
            "direction": self.direction,
            "feature_value": self.feature_value,
            "category": self.category,
            "search_hint": self.search_hint,
        }


@dataclass(slots=True)
class CorpusChunk:
    chunk_id: str
    source: str
    category: str
    title: str
    text: str

    @property
    def word_count(self) -> int:
        return len(self.text.split())


@dataclass(slots=True)
class RetrievedDocument:
    chunk_id: str
    text: str
    source: str
    category: str
    title: str
    score: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source": self.source,
            "category": self.category,
            "title": self.title,
            "score": float(self.score),
        }
