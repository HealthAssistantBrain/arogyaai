"""Utility helpers for the storage pipeline."""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_storage_pipeline_context() -> dict[str, str]:
    return {
        "pipeline": "storage_pipeline",
        "mode": "db_write",
    }


def serialize_for_json(obj: Any):
    if isinstance(obj, datetime):
        return _normalize_datetime(obj).isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, Enum):
        return serialize_for_json(obj.value)
    if isinstance(obj, BaseModel):
        return serialize_for_json(obj.model_dump(mode="json"))
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {str(key): serialize_for_json(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [serialize_for_json(item) for item in obj]
    if hasattr(obj, "item") and callable(getattr(obj, "item")):
        try:
            return serialize_for_json(obj.item())
        except Exception:
            pass
    if hasattr(obj, "tolist") and callable(getattr(obj, "tolist")):
        try:
            return serialize_for_json(obj.tolist())
        except Exception:
            pass
    return obj


def ensure_json_safe(obj: Any) -> Any:
    return json.loads(json.dumps(serialize_for_json(obj), allow_nan=False))
