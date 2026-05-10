from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from models.memory import EmotionalMemoryRecord

from .memory_types import EmotionalMemory, EmotionalTone, MemoryImportance, MemoryType

if TYPE_CHECKING:
    from .memory_embeddings import MemoryEmbeddingService

logger = logging.getLogger("uvicorn.error")

_ANXIETY_PATTERNS = re.compile(r"\b(?:scared|worried|anxious|nervous|afraid|panicking|really concerned|serious)\b", re.IGNORECASE)
_DISTRESS_PATTERNS = re.compile(r"\b(?:overwhelmed|can't cope|can't handle|hopeless|so stressed|breaking down)\b", re.IGNORECASE)
_FRUSTRATION_PATTERNS = re.compile(r"\b(?:frustrated|nothing helps|not getting better|still the same|no improvement)\b", re.IGNORECASE)
_REASSURED_PATTERNS = re.compile(r"\b(?:that helps|i feel better|reassuring|much clearer now|relieved)\b", re.IGNORECASE)


class EmotionalMemoryModule:
    def __init__(self, session_factory, embeddings: MemoryEmbeddingService) -> None:
        self._session_factory = session_factory
        self._embeddings = embeddings

    async def detect_and_store(
        self,
        user_id: str,
        session_id: str,
        user_input: str,
        *,
        topic_context: str = "",
    ) -> EmotionalMemory | None:
        tone, intensity = _detect_tone(user_input)
        if tone == EmotionalTone.NEUTRAL or intensity < 0.3:
            return None
        memory = await asyncio.to_thread(self._persist_sync, user_id, session_id, user_input, topic_context, tone, intensity)
        if memory is None:
            return None
        if intensity >= 0.6:
            embedding_id = await self._embeddings.embed_and_store(memory)
            if embedding_id:
                await asyncio.to_thread(self._set_embedding_id_sync, memory.id, embedding_id)
                memory.embedding_id = embedding_id
        return memory

    async def get_dominant_emotional_context(self, user_id: str) -> EmotionalMemory | None:
        return await asyncio.to_thread(self._get_dominant_sync, user_id)

    def get_tone_adaptation(self, emotional: EmotionalMemory | None) -> dict[str, str]:
        if emotional is None:
            return {}
        mapping = {
            EmotionalTone.ANXIOUS: {
                "tone_modifier": "reassuring and calm",
                "response_length": "moderate",
                "extra_instruction": "Acknowledge the user's anxiety explicitly before answering.",
            },
            EmotionalTone.DISTRESSED: {
                "tone_modifier": "warm and supportive",
                "response_length": "moderate",
                "extra_instruction": "Check in on the user's wellbeing before diving into information.",
            },
            EmotionalTone.FRUSTRATED: {
                "tone_modifier": "clear and direct",
                "response_length": "brief",
                "extra_instruction": "Get to the point quickly and avoid a long preamble.",
            },
            EmotionalTone.CONCERNED: {
                "tone_modifier": "attentive and careful",
                "response_length": "detailed",
                "extra_instruction": "Address the user's specific concern before broadening the discussion.",
            },
        }
        return mapping.get(emotional.emotional_tone, {})

    def _persist_sync(
        self,
        user_id: str,
        session_id: str,
        user_input: str,
        topic_context: str,
        tone: EmotionalTone,
        intensity: float,
    ) -> EmotionalMemory | None:
        topic = topic_context or _infer_topic(user_input)
        memory = EmotionalMemory(
            user_id=user_id,
            session_id=session_id,
            memory_type=MemoryType.EMOTIONAL,
            importance=MemoryImportance.HIGH if intensity >= 0.7 else MemoryImportance.MEDIUM,
            content=f"User expressed {tone.value} about {topic}",
            emotional_tone=tone,
            trigger_topic=topic,
            intensity=intensity,
            resolved=tone == EmotionalTone.REASSURED,
            created_at=datetime.now(timezone.utc),
            decay_score=1.0,
        )
        db = self._session_factory()
        try:
            db.add(
                EmotionalMemoryRecord(
                    id=memory.id,
                    user_id=user_id,
                    session_id=session_id,
                    emotional_tone=tone.value,
                    trigger_topic=topic,
                    intensity=intensity,
                    adaptation_applied="",
                    resolved=memory.resolved,
                    decay_score=1.0,
                    created_at=memory.created_at,
                )
            )
            db.commit()
            return memory
        except Exception as exc:
            db.rollback()
            logger.error("Emotional memory write failed for user=%s: %s", user_id, exc, exc_info=True)
            return None
        finally:
            db.close()

    def _get_dominant_sync(self, user_id: str) -> EmotionalMemory | None:
        db = self._session_factory()
        try:
            row = (
                db.query(EmotionalMemoryRecord)
                .filter(
                    EmotionalMemoryRecord.user_id == user_id,
                    EmotionalMemoryRecord.resolved.is_(False),
                    EmotionalMemoryRecord.intensity >= 0.5,
                    EmotionalMemoryRecord.decay_score > 0.2,
                )
                .order_by(EmotionalMemoryRecord.intensity.desc(), EmotionalMemoryRecord.created_at.desc())
                .first()
            )
            if row is None:
                return None
            created_at = row.created_at or datetime.now(timezone.utc)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            return EmotionalMemory(
                id=str(row.id),
                user_id=str(row.user_id),
                memory_type=MemoryType.EMOTIONAL,
                importance=MemoryImportance.MEDIUM,
                content=f"Emotional context: {row.emotional_tone}",
                emotional_tone=EmotionalTone(str(row.emotional_tone)),
                trigger_topic=row.trigger_topic or "",
                intensity=float(row.intensity or 0.5),
                adaptation_applied=row.adaptation_applied or "",
                resolved=bool(row.resolved),
                created_at=created_at,
                decay_score=float(row.decay_score or 1.0),
                embedding_id=row.embedding_id,
                session_id=row.session_id,
            )
        except Exception as exc:
            logger.warning("Emotional context retrieval failed for user=%s: %s", user_id, exc)
            return None
        finally:
            db.close()

    def _set_embedding_id_sync(self, memory_id: str, embedding_id: str) -> None:
        db = self._session_factory()
        try:
            row = db.query(EmotionalMemoryRecord).filter(EmotionalMemoryRecord.id == memory_id).one_or_none()
            if row is not None:
                row.embedding_id = embedding_id
                db.commit()
        except Exception:
            db.rollback()
            logger.warning("Failed to attach emotional embedding id=%s", memory_id, exc_info=True)
        finally:
            db.close()


def _detect_tone(text: str) -> tuple[EmotionalTone, float]:
    scores = {
        EmotionalTone.ANXIOUS: len(_ANXIETY_PATTERNS.findall(text or "")) * 0.3,
        EmotionalTone.DISTRESSED: len(_DISTRESS_PATTERNS.findall(text or "")) * 0.4,
        EmotionalTone.FRUSTRATED: len(_FRUSTRATION_PATTERNS.findall(text or "")) * 0.25,
        EmotionalTone.REASSURED: len(_REASSURED_PATTERNS.findall(text or "")) * 0.2,
    }
    dominant = max(scores, key=scores.get)
    max_score = scores[dominant]
    if max_score <= 0:
        return EmotionalTone.NEUTRAL, 0.0
    return dominant, min(1.0, max_score)


def _infer_topic(text: str) -> str:
    lowered = str(text or "").lower()
    topics = ["blood pressure", "heart", "diabetes", "glucose", "sleep", "weight", "kidney", "liver", "chest"]
    for topic in topics:
        if topic in lowered:
            return topic
    words = str(text or "").split()
    return " ".join(words[:5]) if words else "general health"
