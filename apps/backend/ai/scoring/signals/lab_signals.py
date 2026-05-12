from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from models import LabResult, User


def _normalize_name(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _metric_key(name: str) -> str | None:
    normalized = _normalize_name(name)
    aliases = {
        "glucose": ("glucose", "blood sugar", "fbs", "rbs"),
        "hba1c": ("hba1c", "a1c"),
        "cholesterol": ("cholesterol", "ldl", "hdl", "triglyceride"),
        "triglycerides": ("triglyceride",),
        "crp": ("crp", "c reactive protein"),
    }
    for metric, keywords in aliases.items():
        if any(keyword in normalized for keyword in keywords):
            return metric
    return None


class LabSignalCollector:
    @staticmethod
    def collect(db: Session, user: User, *, days: int = 30) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
        rows = (
            db.query(LabResult)
            .filter(LabResult.user_id == user.id, LabResult.timestamp >= cutoff)
            .order_by(LabResult.timestamp.asc())
            .all()
        )
        histories: dict[str, list[float]] = defaultdict(list)
        latest: dict[str, dict[str, Any]] = {}

        for row in rows:
            metric_key = _metric_key(row.name)
            if metric_key is None:
                continue
            if row.value is not None:
                histories[metric_key].append(float(row.value))
            latest[metric_key] = {
                "name": row.name,
                "value": _safe_float(row.value),
                "unit": row.unit,
                "status": row.status,
                "reference_range": row.reference_range,
                "timestamp": row.timestamp,
            }

        return {
            "current": {
                "glucose": latest.get("glucose", {}).get("value"),
                "hba1c": latest.get("hba1c", {}).get("value"),
                "cholesterol": latest.get("cholesterol", {}).get("value"),
                "triglycerides": latest.get("triglycerides", {}).get("value"),
                "crp": latest.get("crp", {}).get("value"),
            },
            "histories": {key: [float(value) for value in values] for key, values in histories.items()},
            "details": latest,
            "source_coverage": {"labs": bool(rows), "glucose": "glucose" in latest, "lipids": "cholesterol" in latest},
            "row_count": len(rows),
            "latest_observation_at": max(
                [item.get("timestamp") for item in latest.values() if item.get("timestamp") is not None],
                default=None,
            ),
        }
