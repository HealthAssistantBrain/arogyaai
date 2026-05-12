from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from cache.recommendations.service import RecommendationSnapshotService, SNAPSHOT_TTL_SECONDS
from cache.recommendations.snapshot_store import RecommendationSnapshotStore
from core.celery_app import celery_app
from database.session import session_scope
from models import User

logger = logging.getLogger("recommendation_tasks")


@celery_app.task(
    bind=True,
    name="workers.recommendation_tasks.refresh_recommendation_snapshot",
)
def refresh_recommendation_snapshot_task(
    self,
    user_id: str,
    prediction_id: str | None = None,
) -> dict[str, Any]:
    with session_scope(label=f"recommendation_snapshot:{user_id}") as db:
        user_uuid = uuid.UUID(str(user_id))
        user = db.query(User).filter(User.id == user_uuid, User.is_deleted == False).first()
        if user is None:
            return {
                "success": False,
                "status": "not_found",
                "message": "User not found for recommendation snapshot refresh.",
            }
        try:
            snapshot = asyncio.run(
                RecommendationSnapshotService.refresh_snapshot(
                    db,
                    user,
                    prediction_id=prediction_id,
                )
            )
        except Exception as exc:
            logger.warning("[FALLBACK SNAPSHOT USED] user=%s reason=celery_refresh_error error=%s", user_id, exc)
            snapshot = RecommendationSnapshotService._fast_snapshot(  # noqa: SLF001
                db,
                user,
                prediction_id=prediction_id,
                source="celery_refresh_fallback",
            )
            asyncio.run(
                RecommendationSnapshotStore.set(
                    RecommendationSnapshotService._cache_key(str(user.id), prediction_id),  # noqa: SLF001
                    snapshot,
                    ttl_seconds=SNAPSHOT_TTL_SECONDS,
                )
            )
        return {
            "success": True,
            "status": "ready",
            "source": "celery",
            "data": snapshot,
        }
