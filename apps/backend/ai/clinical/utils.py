from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import logging
from typing import Any


logger = logging.getLogger("uvicorn.error")

EPSILON = 0.01
RECENT_DAYS = 7
MEDIUM_DAYS = 30

METRIC_SEMANTICS: dict[str, dict[str, Any]] = {
    "heart_rate": {"label": "Heart rate", "unit": "bpm", "lower_is_better": True, "domain": "cardiovascular"},
    "sleep": {"label": "Sleep", "unit": "hours", "lower_is_better": False, "domain": "recovery"},
    "activity": {"label": "Activity", "unit": "steps", "lower_is_better": False, "domain": "behavioral"},
    "spo2": {"label": "SpO2", "unit": "%", "lower_is_better": False, "domain": "respiratory"},
    "blood_pressure_systolic": {"label": "Systolic BP", "unit": "mmHg", "lower_is_better": True, "domain": "cardiovascular"},
    "blood_pressure_diastolic": {"label": "Diastolic BP", "unit": "mmHg", "lower_is_better": True, "domain": "cardiovascular"},
    "glucose": {"label": "Glucose", "unit": "mg/dL", "lower_is_better": True, "domain": "metabolic"},
    "health_score": {"label": "Health score", "unit": "", "lower_is_better": False, "domain": "global"},
    "risk_score": {"label": "Risk score", "unit": "%", "lower_is_better": True, "domain": "global"},
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def dedupe_texts(values: list[Any], *, limit: int = 8) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in values:
        text = safe_text(item)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def percent(value: Any, *, scale_if_fraction: bool = True, precision: int = 1) -> float:
    numeric = safe_float(value, 0.0) or 0.0
    if scale_if_fraction and abs(numeric) <= 1.0:
        numeric *= 100.0
    return round(numeric, precision)


def format_value(value: Any, unit: str | None = None, *, precision: int = 1) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "--"
    if abs(numeric - round(numeric)) < EPSILON:
        rendered = str(int(round(numeric)))
    else:
        rendered = f"{numeric:.{precision}f}"
    suffix = safe_text(unit)
    return f"{rendered} {suffix}".strip()


def normalize_metric_name(name: Any) -> str:
    text = safe_text(name).lower().replace(" ", "_")
    aliases = {
        "steps": "activity",
        "step_count": "activity",
        "sleep_hours": "sleep",
        "sleep_duration": "sleep",
        "resting_hr": "heart_rate",
        "avg_rhr": "heart_rate",
        "bp_systolic": "blood_pressure_systolic",
        "bp_diastolic": "blood_pressure_diastolic",
    }
    return aliases.get(text, text)


def metric_semantics(name: Any) -> dict[str, Any]:
    normalized = normalize_metric_name(name)
    return METRIC_SEMANTICS.get(
        normalized,
        {
            "label": normalized.replace("_", " ").title() or "Metric",
            "unit": "",
            "lower_is_better": False,
            "domain": "general",
        },
    )


def history_points(history: Any) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for item in safe_list(history):
        if not isinstance(item, dict):
            continue
        numeric = safe_float(item.get("value"))
        if numeric is None:
            continue
        points.append(
            {
                "value": numeric,
                "timestamp": parse_datetime(item.get("timestamp")),
                "source": safe_text(item.get("source")),
                "unit": safe_text(item.get("unit")),
            }
        )
    points.sort(key=lambda item: item.get("timestamp") or datetime.min.replace(tzinfo=timezone.utc))
    return points


def classify_trend(metric: Any, history: Any) -> dict[str, Any]:
    normalized = normalize_metric_name(metric)
    semantics = metric_semantics(normalized)
    points = history_points(history)
    latest = points[-1] if points else None
    first = points[0] if points else None
    latest_value = safe_float((latest or {}).get("value"))
    first_value = safe_float((first or {}).get("value"))
    if latest_value is None:
        return {
            "metric": normalized,
            "label": semantics["label"],
            "state": "insufficient_data",
            "domain": semantics["domain"],
            "latest_value": None,
            "baseline_value": None,
            "delta": 0.0,
            "direction": "flat",
            "unit": semantics["unit"],
            "point_count": 0,
            "narrative": f"{semantics['label']} has insufficient longitudinal data for interpretation.",
        }

    delta = round(latest_value - (first_value if first_value is not None else latest_value), 2)
    lower_is_better = bool(semantics["lower_is_better"])
    if abs(delta) <= EPSILON:
        state = "stable"
        direction = "flat"
    else:
        direction = "up" if delta > 0 else "down"
        improving = delta < 0 if lower_is_better else delta > 0
        state = "improving" if improving else "deteriorating"

    narrative = (
        f"{semantics['label']} moved from {format_value(first_value, semantics['unit'])} "
        f"to {format_value(latest_value, semantics['unit'])} and is currently {state}."
    )
    return {
        "metric": normalized,
        "label": semantics["label"],
        "state": state,
        "domain": semantics["domain"],
        "latest_value": latest_value,
        "baseline_value": first_value,
        "delta": delta,
        "direction": direction,
        "unit": semantics["unit"],
        "point_count": len(points),
        "latest_timestamp": (latest or {}).get("timestamp").isoformat() if (latest or {}).get("timestamp") else None,
        "narrative": narrative,
    }


def within_days(value: Any, days: int) -> bool:
    parsed = parse_datetime(value)
    if parsed is None:
        return False
    return parsed >= utc_now() - timedelta(days=max(1, days))


def sort_events(events: list[dict[str, Any]], *, reverse: bool = False) -> list[dict[str, Any]]:
    return sorted(
        [item for item in events if isinstance(item, dict)],
        key=lambda item: parse_datetime(item.get("event_date") or item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=reverse,
    )


def event_severity_rank(value: Any) -> int:
    normalized = safe_text(value).lower()
    if normalized in {"critical", "emergency"}:
        return 4
    if normalized in {"high", "urgent"}:
        return 3
    if normalized in {"moderate", "warning"}:
        return 2
    if normalized in {"low", "info"}:
        return 1
    return 0


def risk_label(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 40:
        return "moderate"
    return "low"


def fingerprint(*values: Any) -> str:
    parts = [safe_text(item) if not isinstance(item, (dict, list, tuple)) else str(item) for item in values]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def evidence_from_event(event: dict[str, Any], *, note: str = "") -> dict[str, Any]:
    return {
        "reference_id": safe_text(event.get("id")),
        "title": safe_text(event.get("title"), "Clinical event"),
        "source": safe_text(event.get("source") or event.get("type"), "timeline"),
        "timestamp": safe_text(event.get("event_date") or event.get("timestamp")),
        "excerpt": safe_text(note or event.get("description") or event.get("summary")),
    }


def structured_log(tag: str, **fields: Any) -> None:
    payload = " ".join(f"{key}={value}" for key, value in fields.items() if value not in (None, ""))
    logger.info("%s %s", tag, payload)
