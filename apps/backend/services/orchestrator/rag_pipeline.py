from __future__ import annotations

import asyncio
import hashlib
import json
import time
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
        self.cache_ttl_seconds = max(30.0, float(getattr(self.settings, "provider_cache_ttl_seconds", 300) or 300))
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._inflight: dict[str, asyncio.Task] = {}

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
        lifecycle_key: str | None = None,
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

        cache_key = self._cache_key(
            workflow=workflow,
            query=query,
            lifecycle_key=lifecycle_key,
            symptom_payload=symptom_payload,
            ml_data=ml_data,
        )
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        task = self._inflight.get(cache_key)
        if task is None or task.done():
            task = asyncio.create_task(
                self._retrieve_uncached(
                    workflow=workflow,
                    query=query,
                    symptom_payload=symptom_payload,
                    ml_data=ml_data,
                    user_context=user_context,
                    top_k=top_k,
                )
            )
            self._inflight[cache_key] = task

        try:
            payload = await task
        finally:
            current = self._inflight.get(cache_key)
            if current is task and task.done():
                self._inflight.pop(cache_key, None)

        self._cache_set(cache_key, payload)
        return dict(payload)

    async def retrieve_report_context(self, structured_data: dict[str, Any], *, lifecycle_key: str | None = None) -> dict[str, Any]:
        query = self.build_report_query(structured_data)
        return await self.retrieve(workflow="report_summary", query=query, top_k=4, lifecycle_key=lifecycle_key)

    async def retrieve_ai_insight_context(
        self,
        shap_values: list[dict[str, Any]],
        *,
        lifecycle_key: str | None = None,
    ) -> dict[str, Any]:
        query_payload = build_query_from_shap(shap_values, limit=self.settings.top_feature_count)
        context = await self.retrieve(
            workflow="ai_insights",
            query=str(query_payload.get("query") or "").strip(),
            top_k=4,
            lifecycle_key=lifecycle_key,
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

    async def _retrieve_uncached(
        self,
        *,
        workflow: str,
        query: str,
        symptom_payload: dict[str, Any] | None = None,
        ml_data: dict[str, Any] | None = None,
        user_context: dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        if workflow in {"chatbot", "symptom_analysis", "recommendations"}:
            payload = await RAGKnowledgeAgent().run(
                query,
                symptom_payload,
                ml_data=ml_data or {},
                user_context=user_context or {},
            )
            payload["cache_hit"] = False
            return payload

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

    def _cache_key(
        self,
        *,
        workflow: str,
        query: str,
        lifecycle_key: str | None,
        symptom_payload: dict[str, Any] | None,
        ml_data: dict[str, Any] | None,
    ) -> str:
        material = {
            "workflow": workflow,
            "query": str(query or "").strip().lower(),
            "lifecycle_key": str(lifecycle_key or "").strip().lower(),
            "symptom_payload": symptom_payload or {},
            "ml_features": {
                "prediction_id": (ml_data or {}).get("prediction_id"),
                "risk_level": (ml_data or {}).get("risk_level"),
            },
        }
        return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def _cache_get(self, cache_key: str) -> dict[str, Any] | None:
        cached = self._cache.get(cache_key)
        if cached is None:
            return None
        expires_at, payload = cached
        if time.monotonic() >= expires_at:
            self._cache.pop(cache_key, None)
            return None
        return {
            **dict(payload),
            "cache_hit": True,
        }

    def _cache_set(self, cache_key: str, payload: dict[str, Any]) -> None:
        self._cache[cache_key] = (
            time.monotonic() + self.cache_ttl_seconds,
            {
                **dict(payload),
                "cache_hit": False,
            },
        )
