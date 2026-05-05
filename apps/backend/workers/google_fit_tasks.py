from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from core.celery_app import celery_app
from database.session import SessionLocal
from models import GoogleFitConnection, User
from services.google_fit_service import (
    GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
    GOOGLE_FIT_INITIAL_FETCH_WINDOW_DAYS,
    GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS,
    GOOGLE_FIT_MAX_SYNC_RETRIES,
    GOOGLE_FIT_PAGE_SIZE_DAYS,
    GoogleFitService,
)

logger = logging.getLogger("google_fit_tasks")


def _is_user_google_connected(db, user_id: str) -> bool:
    """Check if the user has an active Google Fit connection with valid tokens."""
    try:
        user_uuid = uuid.UUID(str(user_id))
        connection = (
            db.query(GoogleFitConnection)
            .filter(GoogleFitConnection.user_id == user_uuid)
            .first()
        )
        if not connection:
            return False
        if (connection.last_sync_status or "").lower() == "disconnected":
            return False
        if not connection.access_token_encrypted and not connection.refresh_token_encrypted:
            return False
        return True
    except Exception:
        return False


def _acquire_sync_lock(user_id: str, ttl_seconds: int = 300) -> bool:
    """Acquire a Redis-based distributed lock for sync. Returns True if acquired."""
    return GoogleFitService.acquire_sync_lock(user_id, ttl_seconds=ttl_seconds)


def _release_sync_lock(user_id: str) -> None:
    """Release the Redis-based distributed lock for sync."""
    GoogleFitService.release_sync_lock(user_id)


def _is_sync_cancelled(user_id: str) -> bool:
    """Check if sync was cancelled (e.g. by logout/disconnect)."""
    try:
        from core.celery_app import CELERY_BROKER_URL
        import redis

        cancel_key = f"gfit_sync_cancel:{user_id}"
        r = redis.Redis.from_url(CELERY_BROKER_URL.replace("/0", "/2"), decode_responses=True)
        return bool(r.exists(cancel_key))
    except Exception:
        return False


@celery_app.task(
    bind=True,
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": GOOGLE_FIT_MAX_SYNC_RETRIES, "countdown": 5},
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
    retry_count = int(getattr(getattr(self, "request", None), "retries", 0) or 0)
    requested_days = max(1, min(int(days or GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS), GOOGLE_FIT_MAX_FETCH_WINDOW_DAYS))
    task_id = getattr(getattr(self, "request", None), "id", None)

    logger.info(
        "SYNC_REQUEST | task_id=%s | user=%s | timezone=%s | days=%s | retry_count=%s",
        task_id,
        user_id,
        timezone_name,
        requested_days,
        retry_count,
    )

    # ── AUTH GUARD ──────────────────────────────────────────────
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
        _connection, _access_token, blocked_result = asyncio.run(
            GoogleFitService.validate_sync_auth(
                db,
                user,
                timezone_name=timezone_name,
                sync_mode="celery",
            )
        )
        if blocked_result is not None:
            return blocked_result
    finally:
        db.close()

    # ── CANCELLATION CHECK ─────────────────────────────────────
    if _is_sync_cancelled(user_id):
        logger.warning("SYNC_STOPPED_LOGOUT | user=%s | reason=cancelled_before_start", user_id)
        return {
            "success": False,
            "status": "cancelled",
            "message": "SYNC STOPPED - USER LOGGED OUT",
            "user_id": user_id,
        }

    # ── DISTRIBUTED LOCK ───────────────────────────────────────
    if not _acquire_sync_lock(user_id):
        logger.info("SYNC_SKIPPED_LOCK | user=%s | source=celery", user_id)
        return {
            "success": False,
            "status": "skipped",
            "message": "SYNC SKIPPED - ALREADY RUNNING",
            "user_id": user_id,
        }

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

        logger.info("SYNC_START | task_id=%s | user=%s | source=celery | days=%s", task_id, user_id, requested_days)
        result = asyncio.run(
            GoogleFitService.sync_steps_paginated(
                db,
                user,
                timezone_name=timezone_name,
                days=requested_days,
                page_size_days=GOOGLE_FIT_PAGE_SIZE_DAYS,
            )
        )

        logger.info("SYNC_COMPLETE | user=%s | source=celery | status=%s", user_id, result.get("status"))
        return result
    except Exception as exc:
        db.rollback()
        logger.exception(
            "SYNC_FAILED | user=%s | retry_count=%s | error=%s",
            user_id,
            retry_count,
            exc,
        )
        try:
            user_uuid = uuid.UUID(str(user_id))
            user = db.query(User).filter(User.id == user_uuid, User.is_deleted == False).first()
            return GoogleFitService.build_fault_tolerant_sync_failure_response(
                db,
                user,
                exc,
                timezone_name=timezone_name,
                retry_count=retry_count,
                operation="celery_sync",
                fallback_used=True,
            )
        except Exception:
            db.rollback()
            logger.exception("[GFitTask] Failed to build isolated failure response | user=%s", user_id)
            return {
                "success": True,
                "status": "failed",
                "wearable_status": "failed",
                "message": "Google Fit sync unavailable",
                "core_system": "healthy",
                "error": str(exc),
                "source": "google_fit",
                "retry_count": retry_count,
                "fallback_used": True,
                "data": [],
            }
    finally:
        end_time = datetime.now(timezone.utc)
        logger.info(
            "SYNC_TASK_FINISHED | user=%s | start_time=%s | end_time=%s | duration=%.3fs",
            user_id,
            start_time.isoformat(),
            end_time.isoformat(),
            time.perf_counter() - start_perf,
        )
        _release_sync_lock(user_id)
        db.close()
