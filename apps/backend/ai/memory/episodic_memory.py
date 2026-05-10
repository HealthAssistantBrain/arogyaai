from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from models.memory import EpisodicMemoryRecord

from .memory_privacy import maybe_decrypt_text, maybe_encrypt_text, sanitize_for_storage
from .memory_ranker import score_importance_from_text
from .memory_types import EpisodicMemory, MemoryImportance, MemoryType

if TYPE_CHECKING:
    from .memory_embeddings import MemoryEmbeddingService

logger = logging.getLogger("uvicorn.error")

_SYMPTOM_PATTERNS = [
    re.compile(
        r"\b(?:chest pain|chest tightness|headache|dizziness|fatigue|nausea|shortness of breath|"
        r"palpitations|blurred vision|numbness|weakness|fever|cough|back pain|joint pain|"
        r"abdominal pain|anxiety|insomnia|swelling|rash|weight loss|weight gain)\b",
        re.IGNORECASE,
    ),
]
_RECOMMENDATION_PATTERNS = [
    re.compile(r"(?:recommend|suggest|advise|encourage)\s+(?:you\s+)?(.{10,120}?)(?:\.|$)", re.IGNORECASE),
    re.compile(r"(?:should|could|might want to)\s+(.{10,120}?)(?:\.|$)", re.IGNORECASE),
]
_IMPORTANCE_ORDER = {
    MemoryImportance.CRITICAL: 4,
    MemoryImportance.HIGH: 3,
    MemoryImportance.MEDIUM: 2,
    MemoryImportance.LOW: 1,
    MemoryImportance.TRIVIAL: 0,
}


class EpisodicMemoryModule:
    def __init__(self, session_factory, embeddings: MemoryEmbeddingService) -> None:
        self._session_factory = session_factory
        self._embeddings = embeddings

    async def write_episode(
        self,
        user_id: str,
        session_id: str,
        user_input: str,
        ai_response: str,
        existing_context: dict | None = None,
    ) -> EpisodicMemory | None:
        episode = await asyncio.to_thread(
            self._persist_episode_sync,
            user_id,
            session_id,
            user_input,
            ai_response,
            existing_context or {},
        )
        if episode is None:
            return None
        embedding_id = await self._embeddings.embed_and_store(episode)
        if embedding_id:
            await asyncio.to_thread(self._set_embedding_id_sync, episode.id, embedding_id)
            episode.embedding_id = embedding_id
        return episode

    async def retrieve_relevant(
        self,
        user_id: str,
        query: str,
        *,
        top_k: int = 5,
        min_importance: MemoryImportance = MemoryImportance.LOW,
    ) -> list[EpisodicMemory]:
        hits = await self._embeddings.search_similar(
            query_text=query,
            user_id=user_id,
            memory_types=["episodic"],
            min_decay=0.1,
            top_k=max(5, top_k * 2),
        )
        point_ids = [str(getattr(hit, "id", "")) for hit in hits if getattr(hit, "id", None)]
        score_lookup = {str(getattr(hit, "id", "")): float(getattr(hit, "score", 0.0) or 0.0) for hit in hits}
        return await asyncio.to_thread(self._retrieve_sync, user_id, point_ids, score_lookup, top_k, min_importance)

    def _persist_episode_sync(
        self,
        user_id: str,
        session_id: str,
        user_input: str,
        ai_response: str,
        existing_context: dict,
    ) -> EpisodicMemory | None:
        symptoms = _extract_symptoms(f"{user_input} {ai_response}")
        recommendations = _extract_recommendations(ai_response)
        summary = sanitize_for_storage(_generate_episode_summary(user_input, symptoms))
        importance = score_importance_from_text(
            f"{user_input} {ai_response}",
            symptoms=symptoms,
            has_recommendations=bool(recommendations),
        )
        if importance == MemoryImportance.TRIVIAL:
            return None

        stored_summary, is_encrypted = maybe_encrypt_text(summary)
        stored_recommendations = [sanitize_for_storage(item) for item in recommendations]
        episode = EpisodicMemory(
            user_id=user_id,
            session_id=session_id,
            memory_type=MemoryType.EPISODIC,
            importance=importance,
            content=summary,
            interaction_summary=summary,
            symptoms_discussed=symptoms,
            recommendations_given=stored_recommendations,
            follow_up_needed=_detect_follow_up_needed(ai_response),
            tags=_extract_tags(symptoms, existing_context),
            created_at=datetime.now(timezone.utc),
            decay_score=1.0,
            is_encrypted=is_encrypted,
        )

        db = self._session_factory()
        try:
            db.add(
                EpisodicMemoryRecord(
                    id=episode.id,
                    user_id=user_id,
                    session_id=session_id,
                    interaction_summary=stored_summary,
                    symptoms_discussed=symptoms,
                    recommendations_given=stored_recommendations,
                    reports_analyzed=[],
                    outcome_noted=None,
                    follow_up_needed=episode.follow_up_needed,
                    importance=importance.value,
                    decay_score=1.0,
                    tags=episode.tags,
                    consent_level=episode.consent_level,
                    is_encrypted=is_encrypted,
                    created_at=episode.created_at,
                )
            )
            db.commit()
            return episode
        except Exception as exc:
            db.rollback()
            logger.error("Failed to persist episodic memory for user=%s: %s", user_id, exc, exc_info=True)
            return None
        finally:
            db.close()

    def _set_embedding_id_sync(self, memory_id: str, embedding_id: str) -> None:
        db = self._session_factory()
        try:
            row = db.query(EpisodicMemoryRecord).filter(EpisodicMemoryRecord.id == memory_id).one_or_none()
            if row is not None:
                row.embedding_id = embedding_id
                db.commit()
        except Exception:
            db.rollback()
            logger.warning("Failed to attach episodic embedding id=%s", memory_id, exc_info=True)
        finally:
            db.close()

    def _retrieve_sync(
        self,
        user_id: str,
        point_ids: list[str],
        score_lookup: dict[str, float],
        top_k: int,
        min_importance: MemoryImportance,
    ) -> list[EpisodicMemory]:
        db = self._session_factory()
        try:
            min_rank = _IMPORTANCE_ORDER[min_importance]
            rows = []
            if point_ids:
                rows = (
                    db.query(EpisodicMemoryRecord)
                    .filter(EpisodicMemoryRecord.user_id == user_id, EpisodicMemoryRecord.id.in_(point_ids))
                    .all()
                )
            if not rows:
                rows = (
                    db.query(EpisodicMemoryRecord)
                    .filter(EpisodicMemoryRecord.user_id == user_id, EpisodicMemoryRecord.decay_score > 0.1)
                    .order_by(EpisodicMemoryRecord.created_at.desc())
                    .limit(top_k)
                    .all()
                )

            now = datetime.now(timezone.utc)
            episodes: list[EpisodicMemory] = []
            for row in rows:
                try:
                    importance = MemoryImportance(str(row.importance or "medium"))
                except ValueError:
                    importance = MemoryImportance.MEDIUM
                if _IMPORTANCE_ORDER[importance] < min_rank:
                    continue
                row.access_count = int(row.access_count or 0) + 1
                row.last_accessed = now
                episodes.append(_row_to_episode(row))
            db.commit()

            def _sort_key(item: EpisodicMemory) -> tuple[float, float, float]:
                created_at = item.created_at if item.created_at.tzinfo else item.created_at.replace(tzinfo=timezone.utc)
                age_days = max(0.0, (now - created_at).total_seconds() / 86400)
                recency = max(0.0, 1.0 - min(age_days / 90.0, 1.0))
                relevance = score_lookup.get(item.id, 0.0)
                importance = _IMPORTANCE_ORDER.get(item.importance, 0)
                combined = (relevance * 0.55) + (recency * 0.25) + (importance / 4.0 * 0.20)
                return (combined, relevance, recency)

            episodes.sort(key=_sort_key, reverse=True)
            return episodes[:top_k]
        except Exception as exc:
            db.rollback()
            logger.error("Episodic retrieval failed for user=%s: %s", user_id, exc, exc_info=True)
            return []
        finally:
            db.close()


def _extract_symptoms(text: str) -> list[str]:
    symptoms = set()
    for pattern in _SYMPTOM_PATTERNS:
        for match in pattern.finditer(text or ""):
            symptoms.add(match.group(0).lower())
    return sorted(symptoms)


def _extract_recommendations(ai_response: str) -> list[str]:
    recommendations: list[str] = []
    seen: set[str] = set()
    for pattern in _RECOMMENDATION_PATTERNS:
        for match in pattern.finditer(ai_response or ""):
            recommendation = match.group(1).strip()
            key = recommendation.lower()
            if 10 < len(recommendation) < 120 and key not in seen:
                seen.add(key)
                recommendations.append(recommendation)
    return recommendations[:5]


def _generate_episode_summary(user_input: str, symptoms: list[str]) -> str:
    snippet = (user_input or "").replace("\n", " ").strip()[:120]
    symptom_text = f" after discussing {', '.join(symptoms[:3])}" if symptoms else ""
    return f"User returned{symptom_text}: {snippet}"


def _detect_follow_up_needed(ai_response: str) -> bool:
    lowered = str(ai_response or "").lower()
    triggers = [
        "follow up",
        "follow-up",
        "check back",
        "monitor this",
        "revisit",
        "let me know how",
        "see a doctor",
        "schedule an appointment",
    ]
    return any(trigger in lowered for trigger in triggers)


def _extract_tags(symptoms: list[str], context: dict | None) -> list[str]:
    tags = set(symptoms)
    context = context or {}
    predictions = context.get("ml_predictions")
    if isinstance(predictions, dict):
        tags.update(str(key) for key in predictions.keys())
    disease_context = context.get("disease_context")
    if disease_context:
        tags.add(str(disease_context))
    return sorted(tags)[:10]


def _row_to_episode(row: EpisodicMemoryRecord) -> EpisodicMemory:
    summary = maybe_decrypt_text(row.interaction_summary, is_encrypted=bool(row.is_encrypted))
    created_at = row.created_at or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return EpisodicMemory(
        id=str(row.id),
        user_id=str(row.user_id),
        session_id=row.session_id,
        memory_type=MemoryType.EPISODIC,
        importance=MemoryImportance(str(row.importance or "medium")),
        content=summary,
        interaction_summary=summary,
        symptoms_discussed=list(row.symptoms_discussed or []),
        recommendations_given=list(row.recommendations_given or []),
        reports_analyzed=list(row.reports_analyzed or []),
        outcome_noted=row.outcome_noted,
        follow_up_needed=bool(row.follow_up_needed),
        tags=list(row.tags or []),
        created_at=created_at,
        last_accessed=row.last_accessed,
        access_count=int(row.access_count or 0),
        decay_score=float(row.decay_score or 1.0),
        embedding_id=row.embedding_id,
        is_encrypted=bool(row.is_encrypted),
        consent_level=str(row.consent_level or "standard"),
    )
