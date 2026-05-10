from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from models.memory import SemanticMemoryRecord
from models import MedicalHistory, UserProfile

from .memory_types import MemoryImportance, MemoryType, SemanticMemory

if TYPE_CHECKING:
    from .memory_embeddings import MemoryEmbeddingService

logger = logging.getLogger("uvicorn.error")

_DETAIL_REQUEST_PATTERNS = re.compile(
    r"\b(?:explain more|tell me more|what does that mean|in detail|elaborate|go deeper|break it down|simpler|plain english)\b",
    re.IGNORECASE,
)
_CLINICAL_LANGUAGE_SIGNALS = re.compile(
    r"\b(?:hba1c|egfr|creatinine|systolic|diastolic|bilirubin|echocardiogram|lipid panel|cbc|troponin)\b",
    re.IGNORECASE,
)


class SemanticMemoryModule:
    def __init__(self, session_factory, embeddings: MemoryEmbeddingService) -> None:
        self._session_factory = session_factory
        self._embeddings = embeddings

    async def get_user_profile(self, user_id: str) -> SemanticMemory | None:
        return await asyncio.to_thread(self._get_user_profile_sync, user_id)

    async def upsert_profile(self, user_id: str, updates: dict[str, object]) -> SemanticMemory | None:
        profile = await asyncio.to_thread(self._upsert_profile_sync, user_id, updates)
        if profile is None:
            return None
        embedding_id = await self._embeddings.embed_and_store(profile)
        if embedding_id:
            await asyncio.to_thread(self._set_embedding_id_sync, user_id, embedding_id)
            profile.embedding_id = embedding_id
        return profile

    def infer_updates_from_interaction(
        self,
        user_input: str,
        ai_response: str,
        existing: SemanticMemory | None,
    ) -> dict[str, object]:
        updates: dict[str, object] = {}
        lowered = str(user_input or "").lower()
        if _DETAIL_REQUEST_PATTERNS.search(user_input or ""):
            updates["preferred_explanation_depth"] = "brief" if "plain english" in lowered or "simpler" in lowered else "detailed"
        if _CLINICAL_LANGUAGE_SIGNALS.search(user_input or ""):
            updates["health_literacy_level"] = "high"
        elif existing and existing.health_literacy_level == "high":
            updates["health_literacy_level"] = "high"

        concern_keywords = ["worried about", "scared of", "keeps happening", "again", "recurring", "chronic"]
        concerns: list[str] = []
        for phrase in concern_keywords:
            if phrase in lowered:
                index = lowered.index(phrase)
                snippet = (user_input or "")[index : index + 64].split(".")[0].strip()
                if 5 < len(snippet) < 64:
                    concerns.append(snippet)
        if concerns:
            updates["recurring_concerns"] = concerns
        return updates

    def _get_user_profile_sync(self, user_id: str) -> SemanticMemory | None:
        db = self._session_factory()
        try:
            record = db.query(SemanticMemoryRecord).filter(SemanticMemoryRecord.user_id == user_id).one_or_none()
            if record is not None:
                return _row_to_semantic(record)
            return self._bootstrap_from_profile_sync(db, user_id)
        except Exception as exc:
            logger.warning("Semantic profile retrieval failed for user=%s: %s", user_id, exc, exc_info=True)
            return None
        finally:
            db.close()

    def _bootstrap_from_profile_sync(self, db, user_id: str) -> SemanticMemory | None:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).one_or_none()
        conditions = [
            item.condition_name
            for item in db.query(MedicalHistory).filter(MedicalHistory.user_id == user_id).all()
            if getattr(item, "condition_name", None)
        ]
        if profile is None and not conditions:
            return None
        lifestyle_notes: list[str] = []
        if getattr(profile, "goals", None):
            lifestyle_notes.append(str(profile.goals))
        if getattr(profile, "activity_level", None):
            lifestyle_notes.append(f"Activity level: {profile.activity_level}")
        return SemanticMemory(
            user_id=user_id,
            memory_type=MemoryType.SEMANTIC,
            importance=MemoryImportance.HIGH,
            content="User semantic profile",
            preferred_explanation_depth="moderate",
            preferred_tone="warm",
            health_literacy_level="medium",
            confirmed_conditions=conditions[:8],
            known_allergies=[str(profile.allergies)] if getattr(profile, "allergies", None) else [],
            lifestyle_notes=lifestyle_notes[:5],
            updated_at=datetime.now(timezone.utc),
        )

    def _upsert_profile_sync(self, user_id: str, updates: dict[str, object]) -> SemanticMemory | None:
        db = self._session_factory()
        try:
            record = db.query(SemanticMemoryRecord).filter(SemanticMemoryRecord.user_id == user_id).one_or_none()
            if record is None:
                seeded = self._bootstrap_from_profile_sync(db, user_id) or SemanticMemory(user_id=user_id, memory_type=MemoryType.SEMANTIC, importance=MemoryImportance.HIGH, content="User semantic profile")
                record = SemanticMemoryRecord(
                    user_id=user_id,
                    preferred_explanation_depth=seeded.preferred_explanation_depth,
                    preferred_tone=seeded.preferred_tone,
                    health_literacy_level=seeded.health_literacy_level,
                    recurring_concerns=seeded.recurring_concerns,
                    confirmed_conditions=seeded.confirmed_conditions,
                    known_allergies=seeded.known_allergies,
                    lifestyle_notes=seeded.lifestyle_notes,
                    communication_preferences=seeded.communication_preferences,
                )
                db.add(record)
                db.flush()

            record.preferred_explanation_depth = str(updates.get("preferred_explanation_depth") or record.preferred_explanation_depth)
            record.preferred_tone = str(updates.get("preferred_tone") or record.preferred_tone)
            record.health_literacy_level = str(updates.get("health_literacy_level") or record.health_literacy_level)
            record.recurring_concerns = _merge_text_lists(record.recurring_concerns, updates.get("recurring_concerns"), limit=20)
            record.confirmed_conditions = _merge_text_lists(record.confirmed_conditions, updates.get("confirmed_conditions"), limit=12)
            record.known_allergies = _merge_text_lists(record.known_allergies, updates.get("known_allergies"), limit=12)
            record.lifestyle_notes = _merge_text_lists(record.lifestyle_notes, updates.get("lifestyle_notes"), limit=10)
            record.communication_preferences = dict(record.communication_preferences or {})
            record.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(record)
            return _row_to_semantic(record)
        except Exception as exc:
            db.rollback()
            logger.error("Semantic profile upsert failed for user=%s: %s", user_id, exc, exc_info=True)
            return None
        finally:
            db.close()

    def _set_embedding_id_sync(self, user_id: str, embedding_id: str) -> None:
        db = self._session_factory()
        try:
            record = db.query(SemanticMemoryRecord).filter(SemanticMemoryRecord.user_id == user_id).one_or_none()
            if record is not None:
                record.embedding_id = embedding_id
                db.commit()
        except Exception:
            db.rollback()
            logger.warning("Failed to attach semantic embedding user=%s", user_id, exc_info=True)
        finally:
            db.close()


def _merge_text_lists(existing, incoming, *, limit: int) -> list[str]:
    values = []
    seen = set()
    for item in list(existing or []) + list(incoming or []):
        text = str(item or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        values.append(text)
        if len(values) >= limit:
            break
    return values


def _row_to_semantic(row: SemanticMemoryRecord) -> SemanticMemory:
    updated_at = row.updated_at or datetime.now(timezone.utc)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return SemanticMemory(
        id=str(row.id),
        user_id=str(row.user_id),
        memory_type=MemoryType.SEMANTIC,
        importance=MemoryImportance.HIGH,
        content="User semantic profile",
        preferred_explanation_depth=row.preferred_explanation_depth or "moderate",
        preferred_tone=row.preferred_tone or "warm",
        health_literacy_level=row.health_literacy_level or "medium",
        recurring_concerns=list(row.recurring_concerns or []),
        confirmed_conditions=list(row.confirmed_conditions or []),
        known_allergies=list(row.known_allergies or []),
        lifestyle_notes=list(row.lifestyle_notes or []),
        communication_preferences=dict(row.communication_preferences or {}),
        updated_at=updated_at,
        embedding_id=row.embedding_id,
        created_at=updated_at,
    )
