from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import TYPE_CHECKING

from models.memory import EpisodicMemoryRecord, HealthMemoryRecord

from .memory_types import HealthMemory, MemoryImportance, MemoryType

if TYPE_CHECKING:
    from .memory_embeddings import MemoryEmbeddingService

logger = logging.getLogger("uvicorn.error")

_LOWER_IS_BETTER = {
    "systolic_bp",
    "diastolic_bp",
    "glucose",
    "bmi",
    "resting_hr",
    "stress_score",
    "cvd_risk",
    "diabetes_risk",
    "hypertension_risk",
    "ckd_risk",
}
_TREND_THRESHOLD_PCT = 5.0


class HealthMemoryModule:
    def __init__(self, session_factory, embeddings: MemoryEmbeddingService) -> None:
        self._session_factory = session_factory
        self._embeddings = embeddings

    async def write_health_point(
        self,
        user_id: str,
        metric_name: str,
        metric_value: float,
        *,
        metric_unit: str = "",
        source: str = "wearable",
        disease_context: str | None = None,
    ) -> HealthMemory | None:
        memory = await asyncio.to_thread(
            self._persist_health_point_sync,
            user_id,
            metric_name,
            metric_value,
            metric_unit,
            source,
            disease_context,
        )
        if memory is None:
            return None
        if memory.importance in {MemoryImportance.HIGH, MemoryImportance.CRITICAL}:
            embedding_id = await self._embeddings.embed_and_store(memory)
            if embedding_id:
                await asyncio.to_thread(self._set_embedding_id_sync, memory.id, embedding_id)
                memory.embedding_id = embedding_id
        return memory

    async def get_trend_context(
        self,
        user_id: str,
        *,
        metrics: list[str] | None = None,
        days: int = 30,
    ) -> list[HealthMemory]:
        return await asyncio.to_thread(self._get_trend_context_sync, user_id, metrics or [], days)

    async def detect_recurring_symptoms(self, user_id: str, *, days: int = 60) -> list[str]:
        return await asyncio.to_thread(self._detect_recurring_symptoms_sync, user_id, days)

    def _persist_health_point_sync(
        self,
        user_id: str,
        metric_name: str,
        metric_value: float,
        metric_unit: str,
        source: str,
        disease_context: str | None,
    ) -> HealthMemory | None:
        db = self._session_factory()
        try:
            baseline = _recent_average(db, user_id, metric_name, days=7)
            trend_direction, trend_note = _compute_trend(metric_name, metric_value, baseline)
            importance = _estimate_health_importance(metric_name, metric_value, trend_direction)
            now = datetime.now(timezone.utc)
            memory = HealthMemory(
                user_id=user_id,
                memory_type=MemoryType.HEALTH,
                importance=importance,
                content=f"{metric_name}: {metric_value} {metric_unit} ({trend_direction})",
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit=metric_unit,
                trend_direction=trend_direction,
                trend_note=trend_note,
                disease_context=disease_context,
                source=source,
                created_at=now,
            )
            db.add(
                HealthMemoryRecord(
                    id=memory.id,
                    user_id=user_id,
                    metric_name=metric_name,
                    metric_value=metric_value,
                    metric_unit=metric_unit,
                    trend_direction=trend_direction,
                    trend_note=trend_note,
                    disease_context=disease_context,
                    source=source,
                    risk_level=memory.risk_level,
                    importance=importance.value,
                    decay_score=1.0,
                    created_at=now,
                )
            )
            db.commit()
            return memory
        except Exception as exc:
            db.rollback()
            logger.error("Health memory write failed for user=%s metric=%s: %s", user_id, metric_name, exc, exc_info=True)
            return None
        finally:
            db.close()

    def _set_embedding_id_sync(self, memory_id: str, embedding_id: str) -> None:
        db = self._session_factory()
        try:
            row = db.query(HealthMemoryRecord).filter(HealthMemoryRecord.id == memory_id).one_or_none()
            if row is not None:
                row.embedding_id = embedding_id
                db.commit()
        except Exception:
            db.rollback()
            logger.warning("Failed to attach health embedding id=%s", memory_id, exc_info=True)
        finally:
            db.close()

    def _get_trend_context_sync(self, user_id: str, metrics: list[str], days: int) -> list[HealthMemory]:
        db = self._session_factory()
        try:
            since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
            query = db.query(HealthMemoryRecord).filter(
                HealthMemoryRecord.user_id == user_id,
                HealthMemoryRecord.created_at >= since,
            )
            if metrics:
                query = query.filter(HealthMemoryRecord.metric_name.in_(metrics))
            rows = query.order_by(HealthMemoryRecord.metric_name.asc(), HealthMemoryRecord.created_at.asc()).all()
            grouped: dict[str, list[HealthMemoryRecord]] = {}
            for row in rows:
                grouped.setdefault(str(row.metric_name), []).append(row)

            results: list[HealthMemory] = []
            for metric_name, items in grouped.items():
                values = [float(item.metric_value) for item in items if item.metric_value is not None]
                if not values:
                    continue
                first = values[0]
                latest = values[-1]
                trend, note = _compute_trend(metric_name, latest, first)
                latest_row = items[-1]
                results.append(
                    HealthMemory(
                        user_id=user_id,
                        memory_type=MemoryType.HEALTH,
                        importance=MemoryImportance.MEDIUM,
                        content=_generate_trend_narrative(metric_name, latest, latest_row.metric_unit or "", trend, days, len(values)),
                        metric_name=metric_name,
                        metric_value=latest,
                        metric_unit=latest_row.metric_unit or "",
                        trend_direction=trend,
                        trend_note=note,
                        disease_context=latest_row.disease_context,
                        source=latest_row.source or "wearable",
                        created_at=latest_row.created_at or datetime.now(timezone.utc),
                    )
                )
            return results
        except Exception as exc:
            logger.error("Health trend retrieval failed for user=%s: %s", user_id, exc, exc_info=True)
            return []
        finally:
            db.close()

    def _detect_recurring_symptoms_sync(self, user_id: str, days: int) -> list[str]:
        db = self._session_factory()
        try:
            since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
            rows = (
                db.query(EpisodicMemoryRecord)
                .filter(EpisodicMemoryRecord.user_id == user_id, EpisodicMemoryRecord.created_at >= since)
                .all()
            )
            counts: dict[str, int] = {}
            for row in rows:
                for symptom in row.symptoms_discussed or []:
                    key = str(symptom).lower()
                    counts[key] = counts.get(key, 0) + 1
            return [symptom for symptom, count in sorted(counts.items(), key=lambda item: item[1], reverse=True) if count >= 3][:10]
        except Exception as exc:
            logger.warning("Recurring symptom detection failed for user=%s: %s", user_id, exc)
            return []
        finally:
            db.close()


def _recent_average(db, user_id: str, metric_name: str, *, days: int) -> float | None:
    since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
    rows = (
        db.query(HealthMemoryRecord.metric_value)
        .filter(
            HealthMemoryRecord.user_id == user_id,
            HealthMemoryRecord.metric_name == metric_name,
            HealthMemoryRecord.created_at >= since,
            HealthMemoryRecord.metric_value.isnot(None),
        )
        .all()
    )
    values = [float(value) for (value,) in rows if value is not None]
    return round(mean(values), 3) if values else None


def _compute_trend(metric_name: str, current_value: float, prior_value: float | None) -> tuple[str, str]:
    if prior_value is None or prior_value == 0:
        return "stable", "Insufficient prior data for trend analysis"
    pct_change = ((current_value - prior_value) / prior_value) * 100
    if abs(pct_change) < _TREND_THRESHOLD_PCT:
        return "stable", f"Stable over observed period ({pct_change:+.1f}%)"
    lower_is_better = metric_name in _LOWER_IS_BETTER
    improving = (pct_change < 0 and lower_is_better) or (pct_change > 0 and not lower_is_better)
    if improving:
        return "improving", f"Improved by {abs(pct_change):.1f}% from prior baseline"
    return "worsening", f"Worsened by {abs(pct_change):.1f}% from prior baseline"


def _estimate_health_importance(metric_name: str, value: float, trend: str) -> MemoryImportance:
    critical_metrics = {"systolic_bp", "diastolic_bp", "spo2", "glucose", "heart_rate"}
    if metric_name in critical_metrics and trend == "worsening":
        return MemoryImportance.HIGH
    if trend in {"worsening", "improving"}:
        return MemoryImportance.MEDIUM
    if metric_name.endswith("_risk") and value >= 0.7:
        return MemoryImportance.HIGH
    return MemoryImportance.LOW


def _generate_trend_narrative(metric_name: str, latest: float, unit: str, trend: str, days: int, readings: int) -> str:
    readable = metric_name.replace("_", " ").title()
    direction = {
        "improving": "has been improving",
        "worsening": "has shown a worsening trend",
        "stable": "has remained stable",
    }.get(trend, "is stable")
    return f"Your {readable} {direction} over the past {days} days (latest: {round(latest, 2)} {unit}, based on {readings} readings)."
