from __future__ import annotations

import math
import logging
from datetime import datetime, timezone

from .memory_types import MemoryImportance

logger = logging.getLogger("uvicorn.error")

_HALF_LIFE_DAYS = {
    MemoryImportance.CRITICAL: 180,
    MemoryImportance.HIGH: 90,
    MemoryImportance.MEDIUM: 30,
    MemoryImportance.LOW: 7,
    MemoryImportance.TRIVIAL: 1,
}
_ACCESS_BOOST = 0.08
_DECAY_FLOOR = 0.05


def compute_decay_score(
    importance: MemoryImportance,
    days_since_creation: float,
    access_count: int = 0,
) -> float:
    half_life = _HALF_LIFE_DAYS.get(importance, 30)
    lambda_value = math.log(2) / half_life
    base_score = math.exp(-lambda_value * max(0.0, days_since_creation))
    access_bonus = min(0.4, max(0, access_count) * _ACCESS_BOOST)
    return max(_DECAY_FLOOR, min(1.0, base_score + access_bonus))


def run_decay_cycle_sync(session_factory) -> dict[str, int]:
    from models.memory import EmotionalMemoryRecord, EpisodicMemoryRecord, HealthMemoryRecord

    table_map = {
        "episodic_memory": EpisodicMemoryRecord,
        "health_memory": HealthMemoryRecord,
        "emotional_memory": EmotionalMemoryRecord,
    }
    now = datetime.now(timezone.utc)
    results: dict[str, int] = {}

    for label, model in table_map.items():
        db = session_factory()
        updated = 0
        try:
            rows = db.query(model).filter(model.decay_score > _DECAY_FLOOR).all()
            for row in rows:
                created_at = row.created_at or now
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                days_old = (now - created_at).total_seconds() / 86400
                row.decay_score = compute_decay_score(
                    MemoryImportance(str(getattr(row, "importance", "medium"))),
                    days_old,
                    int(getattr(row, "access_count", 0) or 0),
                )
                updated += 1
            db.commit()
            results[label] = updated
        except Exception as exc:
            db.rollback()
            logger.error("Memory decay cycle failed for %s: %s", label, exc, exc_info=True)
            results[label] = -1
        finally:
            db.close()
    return results
