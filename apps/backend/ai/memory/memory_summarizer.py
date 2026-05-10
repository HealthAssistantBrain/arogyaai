from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from ai.providers.models.payloads import ProviderRequest
from ai.providers.orchestration.runtime_factory import get_provider_runtime
from models.memory import EpisodicMemoryRecord, MemorySummaryRecord

from .memory_embeddings import MemoryEmbeddingService
from .memory_types import MemoryImportance, MemoryItem, MemoryType

logger = logging.getLogger("uvicorn.error")

SUMMARIZE_MIN_EPISODES = 15
SUMMARIZE_WINDOW_DAYS = 30
_SYSTEM_PROMPT = (
    "Summarize the health interactions into 2-3 concise patient-memory sentences. "
    "Focus on recurring symptoms, meaningful changes, and prior follow-up advice."
)


class MemorySummarizer:
    def __init__(self, session_factory, embeddings: MemoryEmbeddingService) -> None:
        self._session_factory = session_factory
        self._embeddings = embeddings
        self._runtime = get_provider_runtime()

    async def summarize_if_needed(self, user_id: str) -> MemoryItem | None:
        count = await asyncio.to_thread(self._count_recent_episodes_sync, user_id, SUMMARIZE_WINDOW_DAYS)
        if count < SUMMARIZE_MIN_EPISODES:
            return None
        return await self._run_summarization(user_id, SUMMARIZE_WINDOW_DAYS)

    async def _run_summarization(self, user_id: str, days: int) -> MemoryItem | None:
        rows = await asyncio.to_thread(self._fetch_recent_episodes_sync, user_id, days)
        if not rows:
            return None
        input_text = "\n".join(
            f"[{row.created_at.strftime('%b %d')}] {row.interaction_summary}"
            for row in rows
            if row.interaction_summary
        )
        summary_text = await self._generate_summary(input_text)
        if not summary_text:
            summary_text = self._fallback_summary(rows)

        summary = await asyncio.to_thread(self._persist_summary_sync, user_id, rows, summary_text)
        if summary is not None:
            embedding_id = await self._embeddings.embed_and_store(summary)
            if embedding_id:
                await asyncio.to_thread(self._set_embedding_id_sync, summary.id, embedding_id)
                summary.embedding_id = embedding_id
        return summary

    async def _generate_summary(self, input_text: str) -> str | None:
        if not input_text.strip():
            return None
        try:
            response = await self._runtime.execute(
                ProviderRequest.from_legacy(
                    task="summarize",
                    workflow="memory_summary",
                    prompt=input_text,
                    system_prompt=_SYSTEM_PROMPT,
                    require_structured_output=False,
                    allow_fallback=True,
                )
            )
            text = str(response.text or response.content.get("summary") or response.content.get("message") or "").strip()
            return text or None
        except Exception as exc:
            logger.warning("LLM memory summarization failed: %s", exc)
            return None

    def _fallback_summary(self, rows: list[EpisodicMemoryRecord]) -> str:
        symptoms: set[str] = set()
        for row in rows:
            symptoms.update(str(item) for item in (row.symptoms_discussed or []) if item)
        symptom_text = f" Recurring topics included {', '.join(sorted(symptoms)[:5])}." if symptoms else ""
        return f"Over this period there were {len(rows)} health conversations.{symptom_text} Monitoring and follow-up were frequent themes."

    def _count_recent_episodes_sync(self, user_id: str, days: int) -> int:
        db = self._session_factory()
        try:
            since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
            return int(
                db.query(EpisodicMemoryRecord)
                .filter(EpisodicMemoryRecord.user_id == user_id, EpisodicMemoryRecord.created_at >= since)
                .count()
            )
        finally:
            db.close()

    def _fetch_recent_episodes_sync(self, user_id: str, days: int) -> list[EpisodicMemoryRecord]:
        db = self._session_factory()
        try:
            since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
            return (
                db.query(EpisodicMemoryRecord)
                .filter(EpisodicMemoryRecord.user_id == user_id, EpisodicMemoryRecord.created_at >= since)
                .order_by(EpisodicMemoryRecord.created_at.asc())
                .all()
            )
        finally:
            db.close()

    def _persist_summary_sync(self, user_id: str, rows: list[EpisodicMemoryRecord], summary_text: str) -> MemoryItem | None:
        db = self._session_factory()
        try:
            since = min((row.created_at for row in rows if row.created_at), default=datetime.now(timezone.utc))
            until = max((row.created_at for row in rows if row.created_at), default=datetime.now(timezone.utc))
            summary = MemoryItem(
                user_id=user_id,
                memory_type=MemoryType.SUMMARY,
                importance=MemoryImportance.HIGH,
                content=summary_text,
                tags=["health_summary", f"window_{SUMMARIZE_WINDOW_DAYS}d"],
                created_at=datetime.now(timezone.utc),
                decay_score=1.0,
            )
            db.add(
                MemorySummaryRecord(
                    id=summary.id,
                    user_id=user_id,
                    summary_type="health",
                    content=summary_text,
                    covers_from=since,
                    covers_to=until,
                    source_ids=[row.id for row in rows if getattr(row, "id", None)],
                    created_at=summary.created_at,
                )
            )
            for row in rows:
                row.decay_score = min(float(row.decay_score or 1.0), 0.2)
            db.commit()
            return summary
        except Exception as exc:
            db.rollback()
            logger.error("Memory summarization persistence failed for user=%s: %s", user_id, exc, exc_info=True)
            return None
        finally:
            db.close()

    def _set_embedding_id_sync(self, summary_id: str, embedding_id: str) -> None:
        db = self._session_factory()
        try:
            row = db.query(MemorySummaryRecord).filter(MemorySummaryRecord.id == summary_id).one_or_none()
            if row is not None:
                row.embedding_id = embedding_id
                db.commit()
        except Exception:
            db.rollback()
            logger.warning("Failed to attach summary embedding id=%s", summary_id, exc_info=True)
        finally:
            db.close()
