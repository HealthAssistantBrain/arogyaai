"""Core service helpers for the wearable ingestion pipeline."""
from __future__ import annotations

from datetime import date, datetime, timezone
from math import isfinite
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from .schema import WearableVitalRecord


def _safe_zoneinfo(timezone_name: str | None) -> ZoneInfo:
    candidate = str(timezone_name or "UTC").strip() or "UTC"
    try:
        return ZoneInfo(candidate)
    except Exception:
        return ZoneInfo("UTC")


def _coerce_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1000.0
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    return None


def _coerce_day(value: Any, tzinfo: ZoneInfo) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        timestamp = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(tzinfo).date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None

        try:
            return date.fromisoformat(candidate).isoformat()
        except ValueError:
            pass

        try:
            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except ValueError:
            return None

        if parsed.tzinfo:
            return parsed.astimezone(tzinfo).date().isoformat()
        return parsed.date().isoformat()

    return None


def _day_sort_key(value: Any) -> date:
    day = _coerce_day(value, ZoneInfo("UTC"))
    if day is None:
        return date.min
    try:
        return date.fromisoformat(day)
    except ValueError:
        return date.min


def _read_value(data_point: Any, *names: str) -> Any:
    if isinstance(data_point, dict):
        for name in names:
            if name in data_point:
                return data_point.get(name)
        return None

    for name in names:
        if hasattr(data_point, name):
            return getattr(data_point, name)
    return None


def _is_step_point(data_point: Any) -> bool:
    raw_type = _read_value(data_point, "type", "vital_type", "metric_type")
    if raw_type is None:
        return _read_value(data_point, "steps", "step_count") is not None

    value = getattr(raw_type, "value", raw_type)
    return str(value or "").strip().lower() == "steps"


def _coerce_steps(value: Any) -> int | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(numeric):
        return None
    return max(0, int(round(numeric)))


def compute_daily_steps(data_points: Iterable[Any], timezone_name: str | None) -> list[dict[str, int | str]]:
    """Bucket step data by local day and return newest days first."""
    tzinfo = _safe_zoneinfo(timezone_name)
    totals_by_day: dict[str, int] = {}

    for data_point in data_points or []:
        if not _is_step_point(data_point):
            continue

        prebucketed_day = _read_value(data_point, "date", "day", "local_day")
        timestamp = _coerce_timestamp(_read_value(data_point, "timestamp", "recorded_at", "time"))
        timestamp_day = timestamp.astimezone(tzinfo).date().isoformat() if timestamp else None
        day = _coerce_day(prebucketed_day, tzinfo) or timestamp_day
        if day is None:
            continue

        steps = _coerce_steps(_read_value(data_point, "steps", "value", "step_count"))
        if steps is None:
            continue

        totals_by_day[day] = totals_by_day.get(day, 0) + steps

    return [
        {"date": day, "steps": totals_by_day[day]}
        for day in sorted(totals_by_day, key=_day_sort_key, reverse=True)
    ]


def compute_daily_step_summary(data_points: Iterable[Any], timezone_name: str | None) -> dict[str, Any]:
    daily_steps = compute_daily_steps(data_points, timezone_name)
    latest_day = max(daily_steps, key=lambda item: _day_sort_key(item["date"])) if daily_steps else None
    best_day = max(daily_steps, key=lambda item: (int(item["steps"]), _day_sort_key(item["date"]))) if daily_steps else None
    total_steps = sum(int(item["steps"]) for item in daily_steps)
    average_steps = round(total_steps / len(daily_steps)) if daily_steps else 0

    return {
        "daily_steps": daily_steps,
        "latest_day": latest_day,
        "best_day": best_day,
        "total_steps": total_steps,
        "average_steps": average_steps,
    }


class IngestionPipelineService:
    """Validates and normalizes wearable records before storage."""

    @staticmethod
    def normalize_vital_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: dict[tuple[str, object, str], dict[str, Any]] = {}
        for record in records:
            try:
                dto = WearableVitalRecord.model_validate(record)
            except ValidationError:
                continue

            storage_payload = dto.to_storage_dict()
            key = (
                storage_payload["type"],
                storage_payload["timestamp"].astimezone(timezone.utc),
                storage_payload["source"],
            )
            normalized[key] = storage_payload

        return list(normalized.values())
