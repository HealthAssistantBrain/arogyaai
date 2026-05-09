from __future__ import annotations

import asyncio
from typing import Any

from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline.corpus import load_corpus_chunks
from pipelines.rag_pipeline.keyword import keyword_retrieve
from pipelines.rag_pipeline.qdrant import probe_qdrant_health
from pipelines.rag_pipeline.query_builder import build_query_from_shap
from pipelines.rag_pipeline.retriever import MedicalKnowledgeRetriever
from pipelines.rag_pipeline.text_cleaning import clean_source_payload
from services.agents.rag_agent import RAGKnowledgeAgent


class OrchestratorRAGPipeline:
    def __init__(self, settings: RagSettings | None = None):
        self.settings = settings or RagSettings()

    def should_use_rag(self, workflow: str, *, query: str = "", payload: dict[str, Any] | None = None) -> bool:
        if workflow in {"chatbot", "symptom_analysis", "report_summary", "ai_insights"}:
            return True
        if workflow == "recommendations":
            return bool(query.strip())
        return False

    async def retrieve(
        self,
        *,
        workflow: str,
        query: str,
        symptom_payload: dict[str, Any] | None = None,
        ml_data: dict[str, Any] | None = None,
        user_context: dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        if not self.should_use_rag(workflow, query=query, payload=user_context):
            return {
                "query": query,
                "source": "skipped",
                "summary": [],
                "top_chunks": [],
                "documents": [],
                "cache_hit": False,
            }

        if workflow in {"chatbot", "symptom_analysis", "recommendations"}:
            return await RAGKnowledgeAgent().run(
                query,
                symptom_payload,
                ml_data=ml_data or {},
                user_context=user_context or {},
            )

        retriever = MedicalKnowledgeRetriever(self.settings)
        try:
            documents = await asyncio.to_thread(
                retriever.retrieve,
                query,
                top_k=top_k or min(self.settings.top_k, 4),
            )
            source = "hybrid"
            error = None
        except Exception as exc:
            chunks = await asyncio.to_thread(load_corpus_chunks, self.settings)
            documents = await asyncio.to_thread(
                keyword_retrieve,
                query,
                chunks,
                limit=top_k or min(self.settings.top_k, 4),
            )
            source = "lexical_corpus"
            error = str(exc)

        serialized = [clean_source_payload(document.as_dict()) for document in documents[:4]]
        return {
            "query": query,
            "source": source,
            "error": error,
            "documents": serialized,
            "summary": serialized,
            "top_chunks": serialized,
            "cache_hit": False,
        }

    async def retrieve_report_context(self, structured_data: dict[str, Any]) -> dict[str, Any]:
        query = self.build_report_query(structured_data)
        return await self.retrieve(workflow="report_summary", query=query, top_k=4)

    async def retrieve_ai_insight_context(self, shap_values: list[dict[str, Any]]) -> dict[str, Any]:
        query_payload = build_query_from_shap(shap_values, limit=self.settings.top_feature_count)
        context = await self.retrieve(
            workflow="ai_insights",
            query=str(query_payload.get("query") or "").strip(),
            top_k=4,
        )
        context["query_payload"] = query_payload
        return context

    @staticmethod
    def build_report_query(structured_data: dict[str, Any]) -> str:
        biomarkers = structured_data.get("biomarkers") if isinstance(structured_data.get("biomarkers"), list) else []
        names = [str(item.get("name") or item.get("test_name") or "").strip() for item in biomarkers if isinstance(item, dict)]
        abnormal_names = [
            name
            for name, item in zip(names, biomarkers, strict=False)
            if isinstance(item, dict) and str(item.get("status") or "").strip().lower() in {"high", "low", "abnormal", "critical"}
        ]
        terms = [
            str(structured_data.get("test_type") or "medical report"),
            "lab interpretation clinical reference ranges",
            "abnormal biomarkers",
            *abnormal_names,
            *names[:8],
        ]
        return " ".join(term for term in terms if term).strip()

    def health_snapshot(self) -> dict[str, Any]:
        return probe_qdrant_health(self.settings)
