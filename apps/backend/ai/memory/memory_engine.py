from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy import inspect, text

from database.session import SessionLocal, primary_engine
from models.memory import EpisodicMemoryRecord

from .emotional_memory import EmotionalMemoryModule
from .episodic_memory import EpisodicMemoryModule
from .health_memory import HealthMemoryModule
from .memory_embeddings import MemoryEmbeddingService
from .memory_privacy import delete_all_user_memory
from .memory_summarizer import MemorySummarizer
from .memory_types import RetrievedMemoryContext
from .retrieval_memory import MemoryRetrievalEngine, build_redis_client
from .semantic_memory import SemanticMemoryModule

logger = logging.getLogger("uvicorn.error")

_MEMORY_ENGINE = None


class MemoryEngine:
    def __init__(self, session_factory=SessionLocal) -> None:
        self._session_factory = session_factory
        self._enabled = os.getenv("MEMORY_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}
        self._embeddings = MemoryEmbeddingService()
        self._redis = build_redis_client()
        self._retrieval = MemoryRetrievalEngine(session_factory, self._embeddings, redis_client=self._redis)
        self._episodic = EpisodicMemoryModule(session_factory, self._embeddings)
        self._semantic = SemanticMemoryModule(session_factory, self._embeddings)
        self._health = HealthMemoryModule(session_factory, self._embeddings)
        self._emotional = EmotionalMemoryModule(session_factory, self._embeddings)
        self._summarizer = MemorySummarizer(session_factory, self._embeddings)
        self._warmup_done = False
        self._warmup_lock = asyncio.Lock()

    async def warmup(self) -> None:
        if not self._enabled or self._warmup_done:
            return
        async with self._warmup_lock:
            if self._warmup_done:
                return
            try:
                await self._embeddings.ensure_collection()
                self._warmup_done = True
            except Exception as exc:
                logger.warning("Memory engine warmup failed; continuing in degraded mode: %s", exc)

    async def verify_storage(self) -> dict[str, object]:
        if not self._enabled:
            return {
                "status": "skipped",
                "detail": "memory_disabled",
                "table_exists": False,
                "timescale_available": False,
                "hypertable_ready": False,
            }
        return await asyncio.to_thread(self._verify_storage_sync)

    def _verify_storage_sync(self) -> dict[str, object]:
        with primary_engine.connect() as conn:
            inspector = inspect(conn)
            tables = set(inspector.get_table_names())
            if "health_memory" not in tables:
                return {
                    "status": "degraded",
                    "detail": "health_memory_missing",
                    "table_exists": False,
                    "timescale_available": False,
                    "hypertable_ready": False,
                    "pk_columns": [],
                }

            pk_columns = list((inspector.get_pk_constraint("health_memory") or {}).get("constrained_columns") or [])
            timescale_available = bool(
                conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")).scalar()
            )
            hypertable_ready = False
            if timescale_available:
                try:
                    hypertable_ready = bool(
                        conn.execute(
                            text(
                                """
                                SELECT 1
                                FROM timescaledb_information.hypertables
                                WHERE hypertable_schema = current_schema()
                                  AND hypertable_name = 'health_memory'
                                """
                            )
                        ).scalar()
                    )
                except Exception:
                    hypertable_ready = False

            composite_pk_ready = set(pk_columns) == {"id", "created_at"} and len(pk_columns) == 2
            status = "ready" if composite_pk_ready and (hypertable_ready or not timescale_available) else "degraded"
            detail = "hypertable_ready" if hypertable_ready else "timescale_unavailable" if not timescale_available else "hypertable_missing"
            return {
                "status": status,
                "detail": detail,
                "table_exists": True,
                "timescale_available": timescale_available,
                "hypertable_ready": hypertable_ready,
                "pk_columns": pk_columns,
            }

    async def get_context_for_prompt(
        self,
        *,
        user_id: str,
        session_id: str,
        current_query: str,
        health_metrics: list[str] | None = None,
    ) -> RetrievedMemoryContext:
        if not self._enabled:
            return RetrievedMemoryContext()
        await self.warmup()
        try:
            return await self._retrieval.retrieve_for_prompt(
                user_id=user_id,
                session_id=session_id,
                current_query=current_query,
                health_metrics_to_fetch=health_metrics,
            )
        except Exception as exc:
            logger.warning("Memory retrieval failed for user=%s: %s", user_id, exc, exc_info=True)
            return RetrievedMemoryContext()

    async def record_interaction(
        self,
        *,
        user_id: str,
        session_id: str,
        user_input: str,
        ai_response: str,
        vitals: dict[str, float] | None = None,
        ml_predictions: dict[str, object] | None = None,
        context_snapshot: dict | None = None,
    ) -> None:
        if not self._enabled:
            return
        await self.warmup()
        try:
            existing_profile = await self._semantic.get_user_profile(user_id)
            semantic_updates = self._semantic.infer_updates_from_interaction(user_input, ai_response, existing_profile)
            tasks = [
                self._episodic.write_episode(user_id, session_id, user_input, ai_response, {"ml_predictions": ml_predictions or {}}),
                self._semantic.upsert_profile(user_id, semantic_updates),
                self._emotional.detect_and_store(user_id, session_id, user_input),
            ]
            for metric_name, value in (vitals or {}).items():
                if isinstance(value, (int, float)):
                    tasks.append(
                        self._health.write_health_point(
                            user_id,
                            metric_name,
                            float(value),
                            metric_unit=_metric_unit(metric_name),
                        )
                    )
            for disease, prediction in (ml_predictions or {}).items():
                probability = prediction.get("probability") if isinstance(prediction, dict) else prediction
                try:
                    numeric = float(probability)
                except (TypeError, ValueError):
                    continue
                tasks.append(
                    self._health.write_health_point(
                        user_id,
                        f"{disease}_risk",
                        numeric,
                        metric_unit="probability",
                        source="ml_prediction",
                        disease_context=str(disease),
                    )
                )
            if context_snapshot:
                tasks.append(self._retrieval.write_short_term(session_id, context_snapshot))
            await asyncio.gather(*tasks, return_exceptions=True)
            asyncio.create_task(self._summarizer.summarize_if_needed(user_id))
        except Exception as exc:
            logger.warning("Memory write pipeline failed for user=%s: %s", user_id, exc, exc_info=True)

    async def search_personal_context(self, *, user_id: str, query: str, top_k: int = 3) -> list[dict]:
        if not self._enabled:
            return []
        await self.warmup()
        try:
            hits = await self._embeddings.search_similar(
                query_text=query,
                user_id=user_id,
                memory_types=["episodic", "health", "summary"],
                min_decay=0.2,
                top_k=top_k,
            )
            docs: list[dict] = []
            for hit in hits:
                payload = getattr(hit, "payload", None) or {}
                score = float(getattr(hit, "score", 0.0) or 0.0)
                if score < 0.45:
                    continue
                docs.append(
                    {
                        "content": str(payload.get("content_snippet") or ""),
                        "source": "your_history",
                        "source_date": _datestr(payload.get("created_at_ts")),
                        "relevance": round(score, 3),
                        "memory_type": str(payload.get("memory_type") or ""),
                    }
                )
            return docs
        except Exception as exc:
            logger.warning("Personal memory search failed for user=%s: %s", user_id, exc)
            return []

    async def get_tone_adaptation(self, context: RetrievedMemoryContext) -> dict[str, str]:
        return self._emotional.get_tone_adaptation(context.emotional)

    async def delete_all_user_memory(self, user_id: str) -> dict[str, int]:
        await self.warmup()
        return await delete_all_user_memory(
            user_id,
            session_factory=self._session_factory,
            embeddings=self._embeddings,
            redis_client=self._redis,
            audit_log=True,
        )

    async def get_recommendation_tracker(self, user_id: str, *, limit: int = 6) -> list[dict]:
        return await asyncio.to_thread(self._get_recommendation_tracker_sync, user_id, limit)

    def _get_recommendation_tracker_sync(self, user_id: str, limit: int) -> list[dict]:
        db = self._session_factory()
        try:
            rows = (
                db.query(EpisodicMemoryRecord)
                .filter(EpisodicMemoryRecord.user_id == user_id)
                .order_by(EpisodicMemoryRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            items: list[dict] = []
            for row in rows:
                for recommendation in list(row.recommendations_given or [])[:2]:
                    items.append(
                        {
                            "id": f"{row.id}:{recommendation}",
                            "date": row.created_at.isoformat() if row.created_at else None,
                            "recommendation": recommendation,
                            "follow_up_needed": bool(row.follow_up_needed),
                            "status": "follow_up_recommended" if row.follow_up_needed else "logged",
                        }
                    )
            return items[:limit]
        finally:
            db.close()


def get_memory_engine() -> MemoryEngine:
    global _MEMORY_ENGINE
    if _MEMORY_ENGINE is None:
        _MEMORY_ENGINE = MemoryEngine()
    return _MEMORY_ENGINE


def _metric_unit(metric_name: str) -> str:
    mapping = {
        "systolic_bp": "mmHg",
        "diastolic_bp": "mmHg",
        "heart_rate": "bpm",
        "glucose": "mg/dL",
        "sleep_hours": "hours",
        "steps_daily": "steps",
        "resting_hr": "bpm",
    }
    return mapping.get(metric_name, "")


def _datestr(timestamp: object) -> str:
    from datetime import datetime

    try:
        return datetime.fromtimestamp(int(timestamp)).strftime("%b %d, %Y")
    except Exception:
        return "prior session"
