from __future__ import annotations

import asyncio
from typing import Any

from .config import RagSettings
from .generator import ExplanationGenerator
from .query_builder import build_query_from_shap, normalize_shap_inputs
from .retriever import MedicalKnowledgeRetriever


class RagExplanationPipeline:
    def __init__(self, settings: RagSettings | None = None):
        self.settings = settings or RagSettings()
        self.retriever = MedicalKnowledgeRetriever(self.settings)
        self.generator = ExplanationGenerator(self.settings)

    async def explain(
        self,
        *,
        risk_score: float,
        risk_level: str,
        shap_values: list[dict[str, Any]],
    ) -> dict[str, Any]:
        query_payload = build_query_from_shap(
            shap_values,
            limit=self.settings.top_feature_count,
        )
        query = str(query_payload.get("query") or "").strip()
        if not query:
            raise RuntimeError("RAG explanation requires SHAP values with at least one usable feature.")

        documents = await asyncio.to_thread(
            self.retriever.retrieve,
            query,
            top_k=self.settings.top_k,
        )
        if not documents:
            raise RuntimeError("RAG explanation requires retrieved medical documents.")

        signals = normalize_shap_inputs(shap_values, limit=self.settings.top_feature_count)
        generated = await self.generator.generate(
            risk_score=risk_score,
            risk_level=risk_level,
            signals=signals,
            documents=documents,
        )

        return {
            "summary": generated.get("summary") or "",
            "factors": generated.get("factors") or [],
            "recommendations": generated.get("recommendations") or [],
            "sources": [document.as_dict() for document in documents],
            "retrieval": {
                "query": query,
                "top_k": self.settings.top_k,
                "categories": query_payload.get("categories") or [],
            },
            "top_features": [signal.as_dict() for signal in signals],
        }
