from __future__ import annotations

import logging
import math
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from core.config import settings

logger = logging.getLogger(__name__)

try:
    import numpy as np
except Exception:  # pragma: no cover - numpy is optional at import time
    np = None

try:
    from pydantic import BaseModel
except Exception:  # pragma: no cover - pydantic is expected but keep import-safe
    BaseModel = None


_DEBUG_ENVS = {"development", "dev", "local", "test"}


def serialization_debug_enabled() -> bool:
    return str(getattr(settings, "APP_ENV", "production") or "production").strip().lower() in _DEBUG_ENVS


def make_json_safe(value: Any) -> Any:
    state = {"changes": 0}
    safe_value = _make_json_safe(value, seen=set(), state=state, path=())
    if state["changes"] and serialization_debug_enabled():
        logger.debug(
            "[JSON SAFE] normalized payload | root_type=%s changes=%s",
            type(value).__name__,
            state["changes"],
        )
    return safe_value


def _mark_change(state: dict[str, int]) -> None:
    state["changes"] += 1


def _is_numpy_scalar(value: Any) -> bool:
    return np is not None and isinstance(value, np.generic)


def _is_numpy_array(value: Any) -> bool:
    return np is not None and isinstance(value, np.ndarray)


def _format_path(path: tuple[Any, ...]) -> str:
    if not path:
        return "$"

    formatted = "$"
    for segment in path:
        if isinstance(segment, int):
            formatted += f"[{segment}]"
        else:
            formatted += f".{segment}"
    return formatted


def _trace_conversion(value: Any, path: tuple[Any, ...]) -> None:
    if not serialization_debug_enabled():
        return
    logger.debug(
        "[SERIALIZATION TRACE] field=%s type=%s path=%s",
        str(path[-1]) if path else "$",
        type(value).__name__,
        _format_path(path),
    )


def _make_json_safe(value: Any, *, seen: set[int], state: dict[str, int], path: tuple[Any, ...]) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if math.isfinite(value):
            return value
        _mark_change(state)
        return None

    if isinstance(value, Decimal):
        _mark_change(state)
        _trace_conversion(value, path)
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None

    if isinstance(value, (datetime, date, time)):
        _mark_change(state)
        _trace_conversion(value, path)
        return value.isoformat()

    if isinstance(value, UUID):
        _mark_change(state)
        _trace_conversion(value, path)
        return str(value)

    if isinstance(value, Enum):
        _mark_change(state)
        _trace_conversion(value, path)
        return _make_json_safe(value.value, seen=seen, state=state, path=path)

    if isinstance(value, Path):
        _mark_change(state)
        _trace_conversion(value, path)
        return str(value)

    if _is_numpy_scalar(value):
        _mark_change(state)
        _trace_conversion(value, path)
        return _make_json_safe(value.item(), seen=seen, state=state, path=path)

    if _is_numpy_array(value):
        token = id(value)
        if token in seen:
            _mark_change(state)
            if serialization_debug_enabled():
                logger.debug("[JSON SAFE] recursive numpy payload detected | type=%s", type(value).__name__)
            return None
        seen.add(token)
        try:
            _mark_change(state)
            return [
                _make_json_safe(item, seen=seen, state=state, path=path + (index,))
                for index, item in enumerate(value.tolist())
            ]
        finally:
            seen.discard(token)

    if BaseModel is not None and isinstance(value, BaseModel):
        token = id(value)
        if token in seen:
            _mark_change(state)
            if serialization_debug_enabled():
                logger.debug("[JSON SAFE] recursive pydantic payload detected | type=%s", type(value).__name__)
            return None
        seen.add(token)
        try:
            _mark_change(state)
            return _make_json_safe(value.model_dump(mode="python"), seen=seen, state=state, path=path)
        finally:
            seen.discard(token)

    if is_dataclass(value) and not isinstance(value, type):
        token = id(value)
        if token in seen:
            _mark_change(state)
            if serialization_debug_enabled():
                logger.debug("[JSON SAFE] recursive dataclass payload detected | type=%s", type(value).__name__)
            return None
        seen.add(token)
        try:
            _mark_change(state)
            return _make_json_safe(asdict(value), seen=seen, state=state, path=path)
        finally:
            seen.discard(token)

    if isinstance(value, Mapping):
        token = id(value)
        if token in seen:
            _mark_change(state)
            if serialization_debug_enabled():
                logger.debug("[JSON SAFE] recursive mapping payload detected | type=%s", type(value).__name__)
            return None
        seen.add(token)
        try:
            normalized: dict[str, Any] = {}
            for key, item in value.items():
                safe_key = _make_json_safe(key, seen=seen, state=state, path=path + ("<key>",))
                key_path = path + (str(safe_key),)
                normalized[str(safe_key)] = _make_json_safe(item, seen=seen, state=state, path=key_path)
            return normalized
        finally:
            seen.discard(token)

    if isinstance(value, (list, tuple, set, frozenset)):
        token = id(value)
        if token in seen:
            _mark_change(state)
            if serialization_debug_enabled():
                logger.debug("[JSON SAFE] recursive sequence payload detected | type=%s", type(value).__name__)
            return None
        seen.add(token)
        try:
            if not isinstance(value, list):
                _mark_change(state)
            return [
                _make_json_safe(item, seen=seen, state=state, path=path + (index,))
                for index, item in enumerate(value)
            ]
        finally:
            seen.discard(token)

    if hasattr(value, "_asdict"):
        try:
            _mark_change(state)
            return _make_json_safe(value._asdict(), seen=seen, state=state, path=path)
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        token = id(value)
        if token in seen:
            _mark_change(state)
            if serialization_debug_enabled():
                logger.debug("[JSON SAFE] recursive object payload detected | type=%s", type(value).__name__)
            return None
        seen.add(token)
        try:
            public_attrs = {
                key: item
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
            if public_attrs:
                _mark_change(state)
                return _make_json_safe(public_attrs, seen=seen, state=state, path=path)
        except Exception:
            pass
        finally:
            seen.discard(token)

    _mark_change(state)
    return str(value)
