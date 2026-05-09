from __future__ import annotations

import uuid
import logging
import time
import threading
from typing import Any

from .config import RagSettings
from .corpus import load_corpus_chunks
from .embedder import EmbeddingService
from .keyword import keyword_retrieve
from .qdrant import (
    batch_upsert_points,
    count_qdrant_points,
    ensure_qdrant_collection,
    get_cached_qdrant_collection_state,
    is_missing_collection_error,
    mark_qdrant_collection_state,
    query_qdrant_points,
    read_qdrant_collection_state,
    recreate_qdrant_collection,
    scroll_qdrant_points,
)
from .reranker import HybridReranker
from .schemas import RetrievedDocument
from .text_cleaning import clean_label_text, clean_rag_text, clean_retrieved_document

logger = logging.getLogger("uvicorn.error")
_WARNING_CACHE: dict[str, float] = {}
_WARNING_CACHE_LOCK = threading.Lock()


def _log_warning_throttled(key: str, message: str, *args: Any) -> None:
    now = time.monotonic()
    interval_seconds = 20.0
    with _WARNING_CACHE_LOCK:
        last_logged_at = _WARNING_CACHE.get(key, 0.0)
        if now - last_logged_at < interval_seconds:
            return
        _WARNING_CACHE[key] = now
    logger.warning(message, *args)


class MedicalKnowledgeRetriever:
    def __init__(self, settings: RagSettings | None = None):
        self.settings = settings or RagSettings()
        self.embedder = EmbeddingService(self.settings)
        self.reranker = HybridReranker(
            dense_weight=self.settings.dense_weight,
            sparse_weight=self.settings.sparse_weight,
        )

    def _create_collection(self) -> None:
        ensure_qdrant_collection(
            self.settings,
            vector_size=self.settings.embedding_dimensions,
            collection_name=self.settings.collection_name,
            distance_name=self.settings.qdrant_distance_metric,
            recreate_on_mismatch=self.settings.recreate_on_dimension_mismatch,
            allow_fallback=True,
        )
        logger.info(
            "RAG Qdrant collection ready | collection=%s dimensions=%s",
            self.settings.collection_name,
            self.settings.embedding_dimensions,
        )

    def ensure_collection(self) -> None:
        self._create_collection()

    def _runtime_collection_state(self) -> dict[str, Any] | None:
        cached = get_cached_qdrant_collection_state(
            self.settings,
            collection_name=self.settings.collection_name,
            max_age_seconds=self.settings.qdrant_collection_state_ttl_seconds,
            allow_fallback=True,
        )
        if cached is not None:
            return cached
        if not self.settings.qdrant_runtime_existence_check_enabled:
            return None
        try:
            return read_qdrant_collection_state(
                self.settings,
                collection_name=self.settings.collection_name,
                max_age_seconds=self.settings.qdrant_collection_state_ttl_seconds,
                allow_fallback=True,
            )
        except Exception as exc:
            logger.debug(
                "RAG runtime collection metadata check failed | collection=%s error=%s",
                self.settings.collection_name,
                exc,
                exc_info=True,
            )
            return None

    def _assert_runtime_collection_ready(self) -> None:
        state = self._runtime_collection_state()
        if state is None:
            return
        if state.get("exists") is False:
            raise RuntimeError(
                f"RAG Qdrant collection is not initialized for runtime retrieval: {self.settings.collection_name!r}."
            )

    def _point_id(self, chunk_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"arogyaai-rag:{chunk_id}"))

    def _existing_index_state(self) -> dict[str, Any]:
        try:
            vector_count = int(
                count_qdrant_points(
                    self.settings,
                    collection_name=self.settings.collection_name,
                    exact=True,
                    allow_fallback=True,
                ).value
            )
        except Exception:
            vector_count = 0

        payload: dict[str, Any] = {}
        if vector_count:
            try:
                scroll_result = scroll_qdrant_points(
                    self.settings,
                    collection_name=self.settings.collection_name,
                    limit=1,
                    with_payload=True,
                    with_vectors=False,
                    allow_fallback=True,
                )
                points, _ = scroll_result.value
                if points:
                    payload = dict(getattr(points[0], "payload", {}) or {})
            except Exception:
                payload = {}

        return {
            "vector_count": vector_count,
            "index_version": payload.get("index_version"),
            "corpus_chunk_count": payload.get("corpus_chunk_count"),
            "embedding_model": payload.get("embedding_model"),
        }

    def ensure_corpus_indexed(self, *, force: bool = False) -> int:
        from qdrant_client.http import models as rest

        self.ensure_collection()
        chunks = load_corpus_chunks(self.settings)
        existing_state = self._existing_index_state()
        existing_count = int(existing_state["vector_count"])
        index_is_current = (
            existing_count == len(chunks)
            and existing_state.get("index_version") == self.settings.index_version
            and int(existing_state.get("corpus_chunk_count") or 0) == len(chunks)
            and existing_state.get("embedding_model") == self.settings.embedding_model_name
        )
        if index_is_current and not force:
            logger.info(
                "RAG ingestion skipped; Qdrant already populated | collection=%s vectors=%s",
                self.settings.collection_name,
                existing_count,
            )
            return existing_count
        if existing_count > 0 or force:
            recreate_qdrant_collection(
                self.settings,
                vector_size=self.settings.embedding_dimensions,
                collection_name=self.settings.collection_name,
                distance_name=self.settings.qdrant_distance_metric,
                allow_fallback=True,
            )

        vectors = self.embedder.embed_texts([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise RuntimeError("Embedding count did not match corpus chunk count.")

        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            points.append(
                rest.PointStruct(
                    id=self._point_id(chunk.chunk_id),
                    vector=vector,
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "source": chunk.source,
                        "source_url": chunk.source_url,
                        "source_org": chunk.source_org,
                        "category": chunk.category,
                        "topic": chunk.topic,
                        "disease_type": chunk.disease_type,
                        "title": chunk.title,
                        "condition": chunk.condition,
                        "symptoms": list(chunk.symptoms),
                        "risk_factors": list(chunk.risk_factors),
                        "tags": list(chunk.tags),
                        "severity": chunk.severity,
                        "document_ids": list(chunk.document_ids),
                        "corpus_chunk_count": len(chunks),
                        "index_version": self.settings.index_version,
                        "embedding_model": self.settings.embedding_model_name,
                    },
                )
            )

        batch_upsert_points(
            self.settings,
            collection_name=self.settings.collection_name,
            points=points,
            wait=True,
            allow_fallback=True,
        )
        logger.info(
            "RAG ingestion success | collection=%s documents=%s chunks=%s vectors=%s",
            self.settings.collection_name,
            len({document_id for chunk in chunks for document_id in chunk.document_ids}),
            len(chunks),
            len(points),
        )
        return len(points)

    def assert_index_ready(self, *, minimum_vectors: int | None = None, auto_index: bool = True) -> dict[str, Any]:
        expected_chunks = len(load_corpus_chunks(self.settings))
        required_vectors = minimum_vectors or expected_chunks
        if auto_index:
            indexed_vectors = self.ensure_corpus_indexed()
        else:
            self._assert_runtime_collection_ready()
            indexed_vectors = int(self._existing_index_state()["vector_count"])

        if indexed_vectors < required_vectors:
            raise RuntimeError(
                f"RAG Qdrant index is not ready: collection={self.settings.collection_name!r} "
                f"vectors={indexed_vectors} required={required_vectors}."
            )
        return {
            "collection_name": self.settings.collection_name,
            "indexed_vectors": indexed_vectors,
            "expected_chunks": expected_chunks,
            "index_version": self.settings.index_version,
            "qdrant_mode": self.settings.qdrant_mode,
        }

    def _fallback_documents(self, query: str, *, limit: int) -> list[RetrievedDocument]:
        try:
            chunks = load_corpus_chunks(self.settings)
        except Exception as exc:
            logger.exception("RAG fallback corpus load failed: %s", exc)
            return []

        documents = keyword_retrieve(
            query or "general symptoms causes risk factors clinical notes recommendations",
            chunks,
            limit=limit,
        )
        if documents:
            return documents[:limit]

        fallback_documents: list[RetrievedDocument] = []
        for chunk in chunks[:limit]:
            fallback_documents.append(
                RetrievedDocument(
                    chunk_id=chunk.chunk_id,
                    text=clean_rag_text(chunk.text),
                    source=chunk.source,
                    source_url=chunk.source_url,
                    source_org=chunk.source_org,
                    category=chunk.category,
                    topic=chunk.topic,
                    disease_type=chunk.disease_type,
                    title=chunk.title,
                    score=0.0,
                    retrieval_method="corpus_fallback",
                    document_ids=chunk.document_ids,
                    condition=chunk.condition,
                    symptoms=chunk.symptoms,
                    risk_factors=chunk.risk_factors,
                    tags=chunk.tags,
                    severity=chunk.severity,
                )
            )
        return fallback_documents

    def _dense_retrieve(self, query: str, *, limit: int) -> list[RetrievedDocument]:
        started_at = time.perf_counter()
        self._assert_runtime_collection_ready()
        query_vector = self.embedder.embed_query(query)
        if not query_vector:
            return []

        try:
            results = query_qdrant_points(
                self.settings,
                collection_name=self.settings.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
                allow_fallback=True,
            ).value
        except Exception as exc:
            if is_missing_collection_error(exc):
                mark_qdrant_collection_state(
                    self.settings,
                    collection_name=self.settings.collection_name,
                    exists=False,
                    source="runtime_query_failure",
                    error=str(exc),
                    allow_fallback=True,
                )
            raise

        documents: list[RetrievedDocument] = []
        for item in results:
            payload = item.payload or {}
            documents.append(
                RetrievedDocument(
                    chunk_id=str(payload.get("chunk_id") or item.id),
                    text=clean_rag_text(payload.get("text") or ""),
                    source=clean_label_text(payload.get("source") or "unknown", limit=140),
                    source_url=str(payload.get("source_url") or ""),
                    source_org=clean_label_text(payload.get("source_org") or "", limit=140),
                    category=clean_label_text(payload.get("category") or "general", limit=80),
                    topic=clean_label_text(payload.get("topic") or payload.get("category") or "general", limit=120),
                    disease_type=clean_label_text(payload.get("disease_type") or payload.get("category") or "general", limit=80),
                    title=clean_label_text(payload.get("title") or "Medical knowledge", limit=140),
                    score=float(getattr(item, "score", 0.0) or 0.0),
                    dense_score=float(getattr(item, "score", 0.0) or 0.0),
                    retrieval_method="dense",
                    document_ids=tuple(str(value) for value in (payload.get("document_ids") or [])),
                    condition=clean_label_text(payload.get("condition") or "", limit=120),
                    symptoms=tuple(str(value) for value in (payload.get("symptoms") or [])),
                    risk_factors=tuple(str(value) for value in (payload.get("risk_factors") or [])),
                    tags=tuple(str(value) for value in (payload.get("tags") or [])),
                    severity=clean_label_text(payload.get("severity") or "routine", limit=40),
                )
            )
        if documents:
            logger.info(
                "RAG vector retrieval success | collection=%s results=%s latency_ms=%s",
                self.settings.collection_name,
                len(documents),
                round((time.perf_counter() - started_at) * 1000, 2),
            )
        return documents

    def _sparse_retrieve(self, query: str, *, limit: int) -> list[RetrievedDocument]:
        chunks = load_corpus_chunks(self.settings)
        return keyword_retrieve(query, chunks, limit=limit)

    def retrieve_candidates(self, query: str) -> dict[str, Any]:
        if not query.strip():
            return {
                "dense": [],
                "sparse": [],
                "reranked": [],
                "dense_error": None,
            }

        started_at = time.perf_counter()
        dense_documents: list[RetrievedDocument] = []
        dense_error = None
        try:
            dense_documents = self._dense_retrieve(query, limit=self.settings.dense_top_k)
        except Exception as exc:
            dense_error = str(exc)
            _log_warning_throttled(
                f"dense:{self.settings.collection_name}",
                "RAG vector retrieval unavailable; using sparse fallback | collection=%s error=%s",
                self.settings.collection_name,
                exc,
            )

        sparse_documents: list[RetrievedDocument] = []
        sparse_error = None
        try:
            sparse_documents = self._sparse_retrieve(query, limit=self.settings.sparse_top_k)
        except Exception as exc:
            sparse_error = str(exc)
            _log_warning_throttled("sparse:fallback", "RAG sparse retrieval unavailable; using corpus fallback: %s", exc)

        reranked = self.reranker.rerank(
            query,
            dense_documents=dense_documents,
            sparse_documents=sparse_documents,
            candidate_limit=self.settings.rerank_candidate_k,
            final_limit=self.settings.top_k,
        )
        reranked = [clean_retrieved_document(document) for document in reranked]
        if not reranked:
            reranked = self._fallback_documents(query, limit=self.settings.top_k)
            if reranked:
                _log_warning_throttled(
                    f"fallback:{self.settings.collection_name}",
                    "RAG fallback usage | collection=%s source=corpus_fallback results=%s",
                    self.settings.collection_name,
                    len(reranked),
                )
        logger.info(
            "RAG retrieval completed | collection=%s dense_results=%s sparse_results=%s final_results=%s dense_error=%s sparse_error=%s latency_ms=%s",
            self.settings.collection_name,
            len(dense_documents),
            len(sparse_documents),
            len(reranked),
            bool(dense_error),
            bool(sparse_error),
            round((time.perf_counter() - started_at) * 1000, 2),
        )
        return {
            "dense": dense_documents,
            "sparse": sparse_documents,
            "reranked": reranked,
            "dense_error": dense_error,
            "sparse_error": sparse_error,
        }

    def retrieve(self, query: str, *, top_k: int | None = None) -> list[RetrievedDocument]:
        if not query.strip():
            return []

        final_limit = top_k or self.settings.top_k
        candidates = self.retrieve_candidates(query)
        if final_limit == self.settings.top_k:
            return [clean_retrieved_document(document) for document in candidates["reranked"]]

        reranked = self.reranker.rerank(
            query,
            dense_documents=candidates["dense"],
            sparse_documents=candidates["sparse"],
            candidate_limit=self.settings.rerank_candidate_k,
            final_limit=final_limit,
        )
        return [clean_retrieved_document(document) for document in reranked]
