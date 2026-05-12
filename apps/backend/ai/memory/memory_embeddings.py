from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from typing import Any

from ai.providers import get_provider_runtime
from pipelines.rag_pipeline.config import RagSettings
from pipelines.rag_pipeline.qdrant import batch_upsert_points, ensure_qdrant_collection, execute_qdrant_operation, query_qdrant_points

from .memory_types import MemoryItem, QDRANT_MEMORY_COLLECTION

logger = logging.getLogger("uvicorn.error")


class MemoryEmbeddingService:
    def __init__(self) -> None:
        self._settings = RagSettings()
        self._settings.collection_name = os.getenv("QDRANT_COLLECTION_MEMORY", QDRANT_MEMORY_COLLECTION).strip() or QDRANT_MEMORY_COLLECTION
        self._dimension = int(os.getenv("MEMORY_EMBEDDING_DIMENSIONS", str(self._settings.embedding_dimensions)))
        self._runtime = get_provider_runtime(self._settings)

    @property
    def collection_name(self) -> str:
        return self._settings.collection_name

    async def ensure_collection(self) -> None:
        await asyncio.to_thread(
            ensure_qdrant_collection,
            self._settings,
            vector_size=self._dimension,
            collection_name=self.collection_name,
            distance_name="cosine",
            recreate_on_mismatch=False,
        )

    async def embed_and_store(self, memory: MemoryItem) -> str | None:
        vector = await self._generate_embedding(_build_embed_text(memory))
        if not vector:
            return None

        from qdrant_client.http import models as rest

        point = rest.PointStruct(
            id=memory.id,
            vector=vector,
            payload={
                "user_id": memory.user_id,
                "memory_type": memory.memory_type.value,
                "importance": memory.importance.value,
                "created_at_ts": int(memory.created_at.timestamp()),
                "decay_score": float(memory.decay_score),
                "tags": list(memory.tags),
                "content_snippet": memory.content[:240],
                "session_id": memory.session_id or "",
            },
        )
        try:
            await asyncio.to_thread(
                batch_upsert_points,
                self._settings,
                points=[point],
                collection_name=self.collection_name,
                wait=True,
            )
            return memory.id
        except Exception as exc:
            logger.warning("Memory embedding upsert failed for id=%s: %s", memory.id, exc)
            return None

    async def search_similar(
        self,
        *,
        query_text: str,
        user_id: str,
        memory_types: list[str] | None = None,
        min_decay: float = 0.1,
        top_k: int = 10,
    ) -> list[Any]:
        vector = await self._generate_embedding(query_text)
        if not vector:
            return []

        from qdrant_client.http import models as rest

        query_filter = rest.Filter(
            must=[
                rest.FieldCondition(key="user_id", match=rest.MatchValue(value=str(user_id))),
                rest.FieldCondition(key="decay_score", range=rest.Range(gte=float(min_decay))),
            ]
        )

        try:
            result = await asyncio.to_thread(
                query_qdrant_points,
                self._settings,
                query_vector=vector,
                collection_name=self.collection_name,
                limit=max(1, int(top_k) * 2),
                with_payload=True,
                query_filter=query_filter,
                allow_fallback=True,
            )
            hits = list(result.value or [])
            if memory_types:
                wanted = {item.lower() for item in memory_types}
                hits = [
                    hit
                    for hit in hits
                    if str((getattr(hit, "payload", None) or {}).get("memory_type", "")).lower() in wanted
                ]
            return hits[:top_k]
        except Exception as exc:
            logger.warning("Memory vector search failed for user=%s: %s", user_id, exc)
            return []

    async def delete_user_memories(self, user_id: str) -> int:
        from qdrant_client.http import models as rest

        filter_obj = rest.Filter(
            must=[rest.FieldCondition(key="user_id", match=rest.MatchValue(value=str(user_id)))]
        )

        def _operation(client: Any, _target) -> int:
            count_response = client.count(collection_name=self.collection_name, count_filter=filter_obj, exact=True)
            existing = int(getattr(count_response, "count", 0) or 0)
            if existing <= 0:
                return 0
            points, _ = client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_obj,
                limit=existing,
                with_payload=False,
                with_vectors=False,
            )
            point_ids = [getattr(point, "id", None) for point in points or [] if getattr(point, "id", None) is not None]
            if point_ids:
                client.delete(
                    collection_name=self.collection_name,
                    points_selector=rest.PointIdsList(points=point_ids),
                    wait=True,
                )
            return len(point_ids)

        try:
            result = await asyncio.to_thread(
                execute_qdrant_operation,
                self._settings,
                _operation,
                operation_name="memory_delete",
                allow_fallback=True,
            )
            return int(result.value or 0)
        except Exception as exc:
            logger.warning("Memory vector delete failed for user=%s: %s", user_id, exc)
            return 0

    async def _generate_embedding(self, text: str) -> list[float]:
        candidate = str(text or "").strip()
        if not candidate:
            return []
        try:
            vectors = await self._runtime.embeddings([candidate], provider="nvidia")
            if vectors and isinstance(vectors[0], list):
                return _fit_vector(vectors[0], self._dimension)
        except Exception as exc:
            logger.warning("Primary memory embedding failed; falling back to deterministic embedding: %s", exc)
        return _deterministic_embedding(candidate, self._dimension)


def _fit_vector(values: list[float], dimension: int) -> list[float]:
    vector = [float(value) for value in values[:dimension]]
    if len(vector) < dimension:
        vector.extend([0.0] * (dimension - len(vector)))
    return vector


def _deterministic_embedding(text: str, dimension: int) -> list[float]:
    buckets = [0.0] * max(8, dimension)
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        slot = int.from_bytes(digest[:2], "big") % len(buckets)
        buckets[slot] += 1.0
    norm = sum(value * value for value in buckets) ** 0.5 or 1.0
    return [round(value / norm, 6) for value in buckets[:dimension]]


def _build_embed_text(memory: MemoryItem) -> str:
    parts = [memory.content]
    if memory.tags:
        parts.append("tags: " + ", ".join(memory.tags))
    symptoms = getattr(memory, "symptoms_discussed", None)
    if symptoms:
        parts.append("symptoms: " + ", ".join(symptoms))
    metric_name = getattr(memory, "metric_name", None)
    if metric_name:
        parts.append(f"metric: {metric_name}")
    emotional_tone = getattr(memory, "emotional_tone", None)
    if emotional_tone:
        tone_value = getattr(emotional_tone, "value", emotional_tone)
        parts.append(f"emotion: {tone_value}")
    return " | ".join(part for part in parts if part)
