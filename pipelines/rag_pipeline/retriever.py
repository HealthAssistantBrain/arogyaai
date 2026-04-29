from __future__ import annotations

from typing import Any

from .config import RagSettings
from .corpus import load_corpus_chunks
from .embedder import EmbeddingService
from .schemas import RetrievedDocument


class MedicalKnowledgeRetriever:
    def __init__(self, settings: RagSettings | None = None):
        self.settings = settings or RagSettings()
        self.embedder = EmbeddingService(self.settings)

    def _client(self):
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client is required for the RAG retrieval pipeline. "
                "Install backend dependencies before using explanations."
            ) from exc

        return QdrantClient(url=self.settings.qdrant_url, api_key=self.settings.qdrant_api_key)

    def ensure_collection(self) -> None:
        from qdrant_client.http import models as rest

        client = self._client()
        try:
            exists = client.collection_exists(self.settings.collection_name)
        except Exception:
            exists = False

        if not exists:
            client.create_collection(
                collection_name=self.settings.collection_name,
                vectors_config=rest.VectorParams(
                    size=self.settings.embedding_dimensions,
                    distance=rest.Distance.COSINE,
                ),
            )

    def ensure_corpus_indexed(self, *, force: bool = False) -> int:
        from qdrant_client.http import models as rest

        self.ensure_collection()
        client = self._client()
        count_result = client.count(collection_name=self.settings.collection_name, exact=False)
        existing_count = int(getattr(count_result, "count", 0) or 0)
        if existing_count > 0 and not force:
            return existing_count

        chunks = load_corpus_chunks(self.settings)
        vectors = self.embedder.embed_texts([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise RuntimeError("Embedding count did not match corpus chunk count.")

        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            points.append(
                rest.PointStruct(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload={
                        "text": chunk.text,
                        "source": chunk.source,
                        "category": chunk.category,
                        "title": chunk.title,
                    },
                )
            )

        if force and existing_count > 0:
            client.delete(collection_name=self.settings.collection_name, points_selector=rest.FilterSelector(filter=rest.Filter()))

        client.upsert(collection_name=self.settings.collection_name, points=points, wait=True)
        return len(points)

    def retrieve(self, query: str, *, top_k: int | None = None) -> list[RetrievedDocument]:
        if not query.strip():
            return []

        self.ensure_corpus_indexed()
        client = self._client()
        query_vector = self.embedder.embed_query(query)
        if not query_vector:
            return []

        results = client.search(
            collection_name=self.settings.collection_name,
            query_vector=query_vector,
            limit=top_k or self.settings.top_k,
            with_payload=True,
        )

        documents: list[RetrievedDocument] = []
        for item in results:
            payload = item.payload or {}
            documents.append(
                RetrievedDocument(
                    chunk_id=str(item.id),
                    text=str(payload.get("text") or ""),
                    source=str(payload.get("source") or "unknown"),
                    category=str(payload.get("category") or "general"),
                    title=str(payload.get("title") or "Medical knowledge"),
                    score=float(getattr(item, "score", 0.0) or 0.0),
                )
            )
        return documents
