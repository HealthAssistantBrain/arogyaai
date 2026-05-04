from __future__ import annotations

import uuid
import logging
from typing import Any

from .config import RagSettings
from .corpus import load_corpus_chunks
from .embedder import EmbeddingService
from .keyword import keyword_retrieve
from .reranker import HybridReranker
from .schemas import RetrievedDocument
from .text_cleaning import clean_label_text, clean_rag_text, clean_retrieved_document

logger = logging.getLogger("uvicorn.error")


class MedicalKnowledgeRetriever:
    def __init__(self, settings: RagSettings | None = None):
        self.settings = settings or RagSettings()
        self.embedder = EmbeddingService(self.settings)
        self.reranker = HybridReranker(
            dense_weight=self.settings.dense_weight,
            sparse_weight=self.settings.sparse_weight,
        )

    def _client(self):
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client is required for the RAG retrieval pipeline. "
                "Install backend dependencies before using explanations."
            ) from exc

        return QdrantClient(url=self.settings.qdrant_url, api_key=self.settings.qdrant_api_key)

    def _vector_size(self, collection: Any) -> int | None:
        try:
            vectors = collection.config.params.vectors
            if hasattr(vectors, "size"):
                return int(vectors.size)
            if isinstance(vectors, dict) and vectors:
                first_vector = next(iter(vectors.values()))
                return int(getattr(first_vector, "size", 0) or 0)
        except Exception:
            return None
        return None

    def _create_collection(self, client: Any) -> None:
        from qdrant_client.http import models as rest

        client.create_collection(
            collection_name=self.settings.collection_name,
            vectors_config=rest.VectorParams(
                size=self.settings.embedding_dimensions,
                distance=rest.Distance.COSINE,
            ),
        )
        logger.info(
            "RAG Qdrant collection ready | collection=%s dimensions=%s",
            self.settings.collection_name,
            self.settings.embedding_dimensions,
        )

    def ensure_collection(self) -> None:
        client = self._client()
        try:
            exists = client.collection_exists(self.settings.collection_name)
        except Exception:
            exists = False

        if not exists:
            self._create_collection(client)
            return

        collection = client.get_collection(self.settings.collection_name)
        vector_size = self._vector_size(collection)
        if vector_size and vector_size != self.settings.embedding_dimensions:
            if not self.settings.recreate_on_dimension_mismatch:
                raise RuntimeError(
                    f"Qdrant collection {self.settings.collection_name!r} has vector size {vector_size}, "
                    f"but {self.settings.embedding_dimensions} is required by {self.settings.embedding_model_name}."
                )
            client.delete_collection(self.settings.collection_name)
            self._create_collection(client)
            logger.warning(
                "RAG Qdrant collection recreated after dimension mismatch | collection=%s old_dimensions=%s expected_dimensions=%s",
                self.settings.collection_name,
                vector_size,
                self.settings.embedding_dimensions,
            )

    def _point_id(self, chunk_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"arogyaai-rag:{chunk_id}"))

    def _existing_index_state(self, client: Any) -> dict[str, Any]:
        try:
            count_result = client.count(collection_name=self.settings.collection_name, exact=True)
            vector_count = int(getattr(count_result, "count", 0) or 0)
        except Exception:
            vector_count = 0

        payload: dict[str, Any] = {}
        if vector_count:
            try:
                scroll_result = client.scroll(
                    collection_name=self.settings.collection_name,
                    limit=1,
                    with_payload=True,
                    with_vectors=False,
                )
                points = scroll_result[0] if isinstance(scroll_result, tuple) else getattr(scroll_result, "points", [])
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
        client = self._client()
        chunks = load_corpus_chunks(self.settings)
        existing_state = self._existing_index_state(client)
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
        if existing_count > 0:
            client.delete_collection(self.settings.collection_name)
            self._create_collection(client)

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

        client.upsert(collection_name=self.settings.collection_name, points=points, wait=True)
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
            self.ensure_collection()
            indexed_vectors = int(self._existing_index_state(self._client())["vector_count"])

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
        self.ensure_corpus_indexed()
        client = self._client()
        query_vector = self.embedder.embed_query(query)
        if not query_vector:
            return []

        if hasattr(client, "search"):
            results = client.search(
                collection_name=self.settings.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
            )
        else:
            response = client.query_points(
                collection_name=self.settings.collection_name,
                query=query_vector,
                limit=limit,
                with_payload=True,
            )
            results = getattr(response, "points", response)

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
                "RAG vector retrieval success | collection=%s results=%s",
                self.settings.collection_name,
                len(documents),
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

        dense_documents: list[RetrievedDocument] = []
        dense_error = None
        try:
            dense_documents = self._dense_retrieve(query, limit=self.settings.dense_top_k)
        except Exception as exc:
            dense_error = str(exc)
            logger.warning("RAG vector retrieval unavailable; using sparse fallback: %s", exc)

        sparse_documents: list[RetrievedDocument] = []
        sparse_error = None
        try:
            sparse_documents = self._sparse_retrieve(query, limit=self.settings.sparse_top_k)
        except Exception as exc:
            sparse_error = str(exc)
            logger.warning("RAG sparse retrieval unavailable; using corpus fallback: %s", exc)

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
                logger.warning(
                    "RAG fallback usage | collection=%s source=corpus_fallback results=%s",
                    self.settings.collection_name,
                    len(reranked),
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
