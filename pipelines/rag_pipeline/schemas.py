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
    topic: str = "general"
    disease_type: str = "general"
    source_url: str = ""
    source_org: str = ""
    document_ids: tuple[str, ...] = ()
    condition: str = ""
    symptoms: tuple[str, ...] = ()
    risk_factors: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    severity: str = "routine"

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
    topic: str = "general"
    disease_type: str = "general"
    source_url: str = ""
    source_org: str = ""
    retrieval_method: str = "hybrid"
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rerank_score: float = 0.0
    document_ids: tuple[str, ...] = ()
    condition: str = ""
    symptoms: tuple[str, ...] = ()
    risk_factors: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    severity: str = "routine"

    def as_dict(self) -> dict[str, Any]:
        from .text_cleaning import clean_source_payload

        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source": self.source,
            "category": self.category,
            "title": self.title,
            "score": float(self.score),
            "topic": self.topic,
            "disease_type": self.disease_type,
            "source_url": self.source_url,
            "source_org": self.source_org,
            "retrieval_method": self.retrieval_method,
            "dense_score": float(self.dense_score),
            "sparse_score": float(self.sparse_score),
            "rerank_score": float(self.rerank_score),
            "document_ids": list(self.document_ids),
            "condition": self.condition,
            "symptoms": list(self.symptoms),
            "risk_factors": list(self.risk_factors),
            "tags": list(self.tags),
            "severity": self.severity,
            "citation": {
                "source": self.source,
                "title": self.title,
                "url": self.source_url,
            },
        } | clean_source_payload(
            {
                "text": self.text,
                "source": self.source,
                "category": self.category,
                "title": self.title,
                "topic": self.topic,
                "disease_type": self.disease_type,
                "source_org": self.source_org,
                "retrieval_method": self.retrieval_method,
                "tags": list(self.tags),
                "severity": self.severity,
                "citation": {
                    "source": self.source,
                    "title": self.title,
                    "url": self.source_url,
                },
            }
        )
