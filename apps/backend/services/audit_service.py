from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from database.session import SessionLocal
from models import Log

logger = logging.getLogger("audit_service")


def _normalize_user_id(user_id: Any) -> uuid.UUID | None:
    if user_id is None or user_id == "":
        return None
    if isinstance(user_id, uuid.UUID):
        return user_id
    try:
        return uuid.UUID(str(user_id))
    except (TypeError, ValueError):
        logger.warning("[Audit] Invalid user_id supplied for audit log: %r", user_id)
        return None


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def log_event(user_id, action, endpoint, details) -> None:
    db = SessionLocal()
    try:
        db.add(
            Log(
                user_id=_normalize_user_id(user_id),
                action=str(action),
                endpoint=str(endpoint) if endpoint is not None else None,
                details=_json_safe(details) if details is not None else {},
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "[Audit] Failed to persist audit event action=%s endpoint=%s user_id=%s",
            action,
            endpoint,
            user_id,
        )
    finally:
        db.close()
