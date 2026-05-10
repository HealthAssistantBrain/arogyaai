from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger("uvicorn.error")

_PII_PATTERNS = [
    re.compile(r"\b\d{12}\b"),
    re.compile(r"\b\d{10}\b"),
    re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    re.compile(r"\bpassword\s*[:=]\s*\S+\b", re.IGNORECASE),
]
_PII_REPLACEMENT = "[REDACTED-PII]"


def sanitize_for_storage(text: str) -> str:
    sanitized = text or ""
    for pattern in _PII_PATTERNS:
        sanitized = pattern.sub(_PII_REPLACEMENT, sanitized)
    return sanitized


def sanitize_payload_for_storage(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            cleaned[key] = sanitize_for_storage(value)
        elif isinstance(value, list):
            cleaned[key] = [sanitize_for_storage(item) if isinstance(item, str) else item for item in value]
        elif isinstance(value, dict):
            cleaned[key] = sanitize_payload_for_storage(value)
        else:
            cleaned[key] = value
    return cleaned


def assert_user_scope(memory_user_id: str, requesting_user_id: str) -> None:
    if str(memory_user_id) != str(requesting_user_id):
        raise ValueError(f"Memory scope violation: {memory_user_id} != {requesting_user_id}")


def maybe_encrypt_text(text: str) -> tuple[str, bool]:
    secret = os.getenv("MEMORY_ENCRYPTION_KEY", "").strip()
    if not secret or not text:
        return text, False
    try:
        from cryptography.fernet import Fernet  # type: ignore

        token = Fernet(secret.encode("utf-8")).encrypt(text.encode("utf-8"))
        return token.decode("utf-8"), True
    except Exception as exc:
        logger.warning("Memory encryption unavailable; storing sanitized plain text: %s", exc)
        return text, False


def maybe_decrypt_text(text: str, *, is_encrypted: bool) -> str:
    if not is_encrypted or not text:
        return text
    secret = os.getenv("MEMORY_ENCRYPTION_KEY", "").strip()
    if not secret:
        return text
    try:
        from cryptography.fernet import Fernet  # type: ignore

        return Fernet(secret.encode("utf-8")).decrypt(text.encode("utf-8")).decode("utf-8")
    except Exception:
        return text


async def delete_all_user_memory(
    user_id: str,
    *,
    session_factory,
    embeddings,
    redis_client=None,
    audit_log: bool = True,
) -> dict[str, int]:
    from models.memory import (
        EmotionalMemoryRecord,
        EpisodicMemoryRecord,
        HealthMemoryRecord,
        MemoryAuditLogRecord,
        MemorySummaryRecord,
        SemanticMemoryRecord,
    )

    counts: dict[str, int] = {}
    session_ids: list[str] = []

    db = session_factory()
    try:
        session_ids = [
            row[0]
            for row in db.query(EpisodicMemoryRecord.session_id)
            .filter(EpisodicMemoryRecord.user_id == user_id, EpisodicMemoryRecord.session_id.isnot(None))
            .all()
            if row[0]
        ]
        for label, model in (
            ("episodic_memory", EpisodicMemoryRecord),
            ("semantic_memory", SemanticMemoryRecord),
            ("health_memory", HealthMemoryRecord),
            ("emotional_memory", EmotionalMemoryRecord),
            ("memory_summaries", MemorySummaryRecord),
        ):
            counts[label] = int(db.query(model).filter(model.user_id == user_id).delete(synchronize_session=False))
        if audit_log:
            db.add(
                MemoryAuditLogRecord(
                    user_id=user_id,
                    action="delete_all",
                    metadata_json=json.loads(json.dumps({"reason": "user_request"})),
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    counts["qdrant"] = await embeddings.delete_user_memories(user_id)

    if redis_client is not None:
        deleted_keys = 0
        for session_id in session_ids:
            key = f"arogyaai:session:{session_id}:context"
            try:
                deleted_keys += int(await redis_client.delete(key))
            except Exception:
                logger.warning("Redis memory delete failed for key=%s", key, exc_info=True)
        counts["redis"] = deleted_keys

    logger.warning("All memory deleted for user=%s counts=%s", user_id, counts)
    return counts
