from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from core.celery_app import celery_app
from database.session import SessionLocal
from models import User
from services.google_fit_service import (
    GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
    GOOGLE_FIT_INITIAL_FETCH_WINDOW_DAYS,
    GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS,
    GOOGLE_FIT_MAX_SYNC_RETRIES,
    GOOGLE_FIT_PAGE_SIZE_DAYS,
    GoogleFitService,
)

logger = logging.getLogger("google_fit_tasks")


@celery_app.task(
    bind=True,
    autoretry_for=(httpx.TimeoutException, httpx.TransportError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": GOOGLE_FIT_MAX_SYNC_RETRIES},
    name="workers.google_fit_tasks.sync_google_fit_for_user",
)
def sync_google_fit_for_user_task(
    self,
    user_id: str,
    timezone_name: str | None = None,
    days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
) -> dict[str, Any]:
    start_time = datetime.now(timezone.utc)
    start_perf = time.perf_counter()
    requested_days = max(1, min(int(days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS), GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS))
    logger.info(
        "[GFitTask] Sync task started | task_id=%s | user=%s | timezone=%s | days=%s | start_time=%s | max_retries=%s",
        getattr(getattr(self, "request", None), "id", None),
        user_id,
        timezone_name,
        requested_days,
        start_time.isoformat(),
        GOOGLE_FIT_MAX_SYNC_RETRIES,
    )

    db = SessionLocal()
    try:
        user_uuid = uuid.UUID(str(user_id))
        user = db.query(User).filter(User.id == user_uuid, User.is_deleted == False).first()
        if not user:
            return {
                "success": False,
                "status": "not_found",
                "message": "User not found for Google Fit sync",
                "user_id": user_id,
            }

        result = asyncio.run(
            GoogleFitService.sync_steps_paginated(
                db,
                user,
                timezone_name=timezone_name,
                days=requested_days,
                page_size_days=GOOGLE_FIT_PAGE_SIZE_DAYS,
            )
        )
        return result
    except Exception as exc:
        db.rollback()
        try:
            user_uuid = uuid.UUID(str(user_id))
            user = db.query(User).filter(User.id == user_uuid, User.is_deleted == False).first()
            connection = GoogleFitService.get_connection(db, user) if user else None
            if connection:
                raw_payload = GoogleFitService._connection_raw_payload(connection)
                background_sync = raw_payload.get("background_sync") if isinstance(raw_payload, dict) else None
                if isinstance(background_sync, dict):
                    background_sync.update(
                        {
                            "status": "failed",
                            "failed_at": datetime.now(timezone.utc).isoformat(),
                            "error": str(exc),
                        }
                    )
                    raw_payload["background_sync"] = background_sync
                connection.last_sync_status = "failed"
                connection.raw_last_response = raw_payload
                db.add(connection)
                db.commit()
        except Exception:
            db.rollback()
            logger.exception("[GFitTask] Failed to persist sync failure state | user=%s", user_id)
        logger.exception("[GFitTask] Sync task failed | user=%s | error=%s", user_id, exc)
        raise
    finally:
        end_time = datetime.now(timezone.utc)
        logger.info(
            "[GFitTask] Sync task finished | user=%s | start_time=%s | end_time=%s | duration=%.3fs | initial_window_days=%s",
            user_id,
            start_time.isoformat(),
            end_time.isoformat(),
            time.perf_counter() - start_perf,
            min(GOOGLE_FIT_INITIAL_FETCH_WINDOW_DAYS, requested_days),
        )
        db.close()
