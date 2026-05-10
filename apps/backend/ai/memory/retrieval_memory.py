from __future__ import annotations

import asyncio
import json
import logging
import os
import time

try:
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover
    redis_async = None

from models.memory import MemorySummaryRecord

from .emotional_memory import EmotionalMemoryModule
from .episodic_memory import EpisodicMemoryModule
from .health_memory import HealthMemoryModule
from .memory_embeddings import MemoryEmbeddingService
from .memory_types import MEMORY_TOKEN_BUDGET, MemoryImportance, MemoryItem, MemoryType, RetrievedMemoryContext
from .semantic_memory import SemanticMemoryModule

logger = logging.getLogger("uvicorn.error")

_CHARS_PER_TOKEN = 4


class MemoryRetrievalEngine:
    def __init__(self, session_factory, embeddings: MemoryEmbeddingService, redis_client=None) -> None:
        self._session_factory = session_factory
        self._redis = redis_client
        self._episodic = EpisodicMemoryModule(session_factory, embeddings)
        self._semantic = SemanticMemoryModule(session_factory, embeddings)
        self._health = HealthMemoryModule(session_factory, embeddings)
        self._emotional = EmotionalMemoryModule(session_factory, embeddings)

    async def retrieve_for_prompt(
        self,
        user_id: str,
        session_id: str,
        current_query: str,
        *,
        health_metrics_to_fetch: list[str] | None = None,
    ) -> RetrievedMemoryContext:
        started_at = time.perf_counter()
        results = await asyncio.gather(
            self._semantic.get_user_profile(user_id),
            self._emotional.get_dominant_emotional_context(user_id),
            self._episodic.retrieve_relevant(user_id, current_query, top_k=5),
            self._health.get_trend_context(user_id, metrics=health_metrics_to_fetch, days=30),
            self._retrieve_summaries(user_id),
            self._get_short_term(session_id),
            return_exceptions=True,
        )
        semantic, emotional, episodic, health, summaries, short_term = results
        context = RetrievedMemoryContext(
            short_term=[] if isinstance(short_term, Exception) else short_term or [],
            episodic=[] if isinstance(episodic, Exception) else episodic or [],
            semantic=None if isinstance(semantic, Exception) else semantic,
            health_trends=[] if isinstance(health, Exception) else health or [],
            emotional=None if isinstance(emotional, Exception) else emotional,
            summaries=[] if isinstance(summaries, Exception) else summaries or [],
            retrieval_time_ms=(time.perf_counter() - started_at) * 1000,
        )
        prompt = context.to_prompt_string()
        context.token_estimate = len(prompt) // _CHARS_PER_TOKEN
        if context.token_estimate > MEMORY_TOKEN_BUDGET:
            context = self._trim_to_budget(context)
        return context

    async def write_short_term(self, session_id: str, context_snapshot: dict) -> None:
        if self._redis is None:
            return
        key = f"arogyaai:session:{session_id}:context"
        try:
            existing = await self._redis.get(key)
            snapshots = json.loads(existing) if existing else []
            snapshots.append(context_snapshot)
            snapshots = snapshots[-20:]
            await self._redis.setex(key, 7200, json.dumps(snapshots, default=str))
        except Exception as exc:
            logger.warning("Short-term memory write failed for session=%s: %s", session_id, exc)

    def _trim_to_budget(self, context: RetrievedMemoryContext) -> RetrievedMemoryContext:
        while True:
            tokens = len(context.to_prompt_string()) // _CHARS_PER_TOKEN
            if tokens <= MEMORY_TOKEN_BUDGET:
                context.token_estimate = tokens
                return context
            if context.summaries:
                context.summaries = context.summaries[:-1]
            elif len(context.health_trends) > 2:
                context.health_trends = context.health_trends[:-1]
            elif len(context.episodic) > 1:
                context.episodic = context.episodic[:-1]
            elif context.emotional:
                context.emotional = None
            else:
                context.token_estimate = tokens
                return context

    async def _retrieve_summaries(self, user_id: str) -> list[MemoryItem]:
        return await asyncio.to_thread(self._retrieve_summaries_sync, user_id)

    def _retrieve_summaries_sync(self, user_id: str) -> list[MemoryItem]:
        db = self._session_factory()
        try:
            rows = (
                db.query(MemorySummaryRecord)
                .filter(MemorySummaryRecord.user_id == user_id)
                .order_by(MemorySummaryRecord.created_at.desc())
                .limit(3)
                .all()
            )
            items: list[MemoryItem] = []
            for row in rows:
                items.append(
                    MemoryItem(
                        id=str(row.id),
                        user_id=str(row.user_id),
                        memory_type=MemoryType.SUMMARY,
                        importance=MemoryImportance.HIGH,
                        content=row.content or "",
                        created_at=row.created_at,
                        embedding_id=row.embedding_id,
                    )
                )
            return items
        finally:
            db.close()

    async def _get_short_term(self, session_id: str) -> list[MemoryItem]:
        if self._redis is None:
            return []
        key = f"arogyaai:session:{session_id}:context"
        try:
            data = await self._redis.get(key)
            payload = json.loads(data) if data else []
            return [
                MemoryItem(
                    user_id="",
                    memory_type=MemoryType.SHORT_TERM,
                    importance=MemoryImportance.LOW,
                    content=str(item.get("query") or item.get("summary") or ""),
                    structured_data=item,
                )
                for item in payload[-5:]
                if isinstance(item, dict)
            ]
        except Exception:
            return []


def build_redis_client():
    if redis_async is None:
        return None
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()
    try:
        return redis_async.from_url(redis_url, encoding="utf-8", decode_responses=True)
    except Exception:
        logger.warning("Redis memory client unavailable", exc_info=True)
        return None
