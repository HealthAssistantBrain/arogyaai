from __future__ import annotations

import asyncio
import logging
import random
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import joinedload

from database.session import log_pool_snapshot, session_scope
from models import GoogleFitConnection, User
from services.google_fit_service import GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS, GoogleFitService

logger = logging.getLogger("google_fit_worker")

_sync_lock = threading.Lock()
_worker_thread: threading.Thread | None = None
_worker_stop = threading.Event()
_consecutive_worker_failures = 0

_MIN_INTERVAL_SECONDS = 280
_MAX_INTERVAL_SECONDS = 320
_MIN_USER_SYNC_INTERVAL_SECONDS = 300


def _is_user_sync_eligible(user: User, connection: GoogleFitConnection | None) -> bool:
    """Check if a user is eligible for background sync (authenticated + connected)."""
    if not connection:
        return False
    if (connection.last_sync_status or "").lower() == "disconnected":
        return False
    if not connection.access_token_encrypted and not connection.refresh_token_encrypted:
        return False
    return True


def _was_synced_recently(connection: GoogleFitConnection | None) -> bool:
    if not connection or not connection.last_synced_at:
        return False
    last_synced_at = connection.last_synced_at
    if last_synced_at.tzinfo is None:
        last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last_synced_at).total_seconds() < _MIN_USER_SYNC_INTERVAL_SECONDS


def _acquire_user_sync_lock(user_id: str, ttl_seconds: int = 300) -> bool:
    """Acquire a Redis-based distributed lock for a specific user's sync."""
    return GoogleFitService.acquire_sync_lock(user_id, ttl_seconds=ttl_seconds)


def _release_user_sync_lock(user_id: str) -> None:
    """Release the Redis-based distributed lock for a specific user's sync."""
    GoogleFitService.release_sync_lock(user_id)


def _is_sync_cancelled(user_id: str) -> bool:
    """Check if sync was cancelled for this user (e.g. logout/disconnect)."""
    try:
        from core.celery_app import CELERY_BROKER_URL
        import redis

        cancel_key = f"gfit_sync_cancel:{user_id}"
        r = redis.Redis.from_url(CELERY_BROKER_URL.replace("/0", "/2"), decode_responses=True)
        return bool(r.exists(cancel_key))
    except Exception:
        return False


async def _sync_connected_user(db, user: User, connection: GoogleFitConnection | None) -> dict[str, Any]:
    timezone_name = connection.default_timezone if connection else None
    return await GoogleFitService.sync_steps_paginated(
        db,
        user,
        timezone_name=timezone_name,
        days=GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
    )


def _load_connected_user_ids(db) -> list[str]:
    return [
        str(user_id)
        for (user_id,) in (
            db.query(User.id)
            .join(GoogleFitConnection, GoogleFitConnection.user_id == User.id)
            .filter(User.is_deleted == False)
            .all()
        )
    ]


def _load_connected_user(db, user_id: str) -> User | None:
    try:
        user_uuid = uuid.UUID(str(user_id))
    except (TypeError, ValueError):
        return None
    return (
        db.query(User)
        .options(
            joinedload(User.google_fit_connection),
            joinedload(User.user_settings),
        )
        .filter(User.id == user_uuid, User.is_deleted == False)
        .first()
    )


def run_google_fit_sync() -> dict[str, Any]:
    if not _sync_lock.acquire(blocking=False):
        logger.info("SYNC_SKIPPED_ALREADY_RUNNING | scope=global | reason=worker_lock_held")
        return {"success": False, "status": "skipped", "message": "sync already running"}

    try:
        with session_scope(label="google_fit_worker.load_user_ids") as db:
            user_ids = _load_connected_user_ids(db)

        logger.info("AUTO_SYNC_CYCLE_START | eligible_users=%s", len(user_ids))

        synced_users = 0
        skipped_users = 0
        failed_users = 0
        auth_blocked_users = 0

        for user_id_str in user_ids:
            if _worker_stop.is_set():
                logger.info("[GoogleFitWorker] Stop requested mid-cycle; ending current sync cycle early")
                break
            with session_scope(label=f"google_fit_worker.user:{user_id_str}") as db:
                user = _load_connected_user(db, user_id_str)
                if user is None:
                    skipped_users += 1
                    logger.info("SYNC_SKIPPED_NOT_FOUND | user=%s | source=auto_worker", user_id_str)
                    continue

                setting = user.user_settings
                connection = user.google_fit_connection

                # ── AUTH GUARD ─────────────────────────────────────
                if not _is_user_sync_eligible(user, connection):
                    auth_blocked_users += 1
                    logger.info("SYNC_AUTH_FAILED | user=%s | reason=not_eligible", user_id_str)
                    continue

                # ── CANCELLATION CHECK ─────────────────────────────
                if _is_sync_cancelled(user_id_str):
                    skipped_users += 1
                    logger.info("SYNC_STOPPED_LOGOUT | user=%s | reason=cancel_flag_set", user_id_str)
                    continue

                if _was_synced_recently(connection):
                    skipped_users += 1
                    logger.info("SYNC_SKIPPED_RATE_LIMIT | user=%s | source=auto_worker", user_id_str)
                    continue

                # ── PER-USER DISTRIBUTED LOCK ──────────────────────
                if not _acquire_user_sync_lock(user_id_str):
                    skipped_users += 1
                    logger.info("SYNC_SKIPPED_LOCK | user=%s | reason=redis_lock_held", user_id_str)
                    continue

                try:
                    result = asyncio.run(_sync_connected_user(db, user, connection))
                    if result.get("connected") and result.get("last_synced_at"):
                        if setting is not None:
                            setting.last_fetch_at = datetime.now(timezone.utc)
                            db.commit()
                        synced_users += 1
                        logger.info("SYNC_COMPLETE | user=%s | sync_mode=auto", user_id_str)
                    else:
                        skipped_users += 1
                except Exception as exc:
                    failed_users += 1
                    db.rollback()
                    logger.exception("SYNC_FAILED | user=%s | sync_mode=auto | error=%s", user_id_str, exc)
                finally:
                    _release_user_sync_lock(user_id_str)

        summary = {
            "success": failed_users == 0,
            "status": "ready" if failed_users == 0 else "partial",
            "synced_users": synced_users,
            "skipped_users": skipped_users,
            "failed_users": failed_users,
            "auth_blocked_users": auth_blocked_users,
        }
        logger.info(
            "AUTO_SYNC_CYCLE_END | synced=%s skipped=%s failed=%s auth_blocked=%s",
            synced_users,
            skipped_users,
            failed_users,
            auth_blocked_users,
        )
        log_pool_snapshot(force=failed_users > 0)
        return summary
    finally:
        _sync_lock.release()


def _next_interval_seconds() -> int:
    return random.randint(_MIN_INTERVAL_SECONDS, _MAX_INTERVAL_SECONDS)


def _worker_loop() -> None:
    global _consecutive_worker_failures
    logger.info(
        "[GoogleFitWorker] Background loop started | interval=%ss-%ss",
        _MIN_INTERVAL_SECONDS,
        _MAX_INTERVAL_SECONDS,
    )

    while not _worker_stop.is_set():
        cycle_started_at = time.perf_counter()
        try:
            summary = run_google_fit_sync()
            _consecutive_worker_failures = 0
            logger.info(
                "[GoogleFitWorker] Cycle complete | status=%s synced=%s skipped=%s failed=%s duration_ms=%s",
                summary.get("status"),
                summary.get("synced_users", 0),
                summary.get("skipped_users", 0),
                summary.get("failed_users", 0),
                round((time.perf_counter() - cycle_started_at) * 1000, 2),
            )
        except Exception as exc:
            _consecutive_worker_failures += 1
            logger.exception("[GoogleFitWorker] Background sync loop failed: %s", exc)
            backoff_seconds = min(600, _next_interval_seconds() * (2 ** min(_consecutive_worker_failures, 3)))
            logger.warning(
                "[GoogleFitWorker] Applying backoff after failure | failures=%s backoff_seconds=%s",
                _consecutive_worker_failures,
                backoff_seconds,
            )
            if _worker_stop.wait(timeout=backoff_seconds):
                break
            continue

        if _worker_stop.is_set():
            break

        sleep_for = _next_interval_seconds()
        logger.info("[GoogleFitWorker] Sleeping for %ss before next sync", sleep_for)
        if _worker_stop.wait(timeout=sleep_for):
            break

    logger.info("[GoogleFitWorker] Background loop stopped")


def start_google_fit_worker() -> threading.Thread | None:
    global _worker_thread

    if _worker_thread and _worker_thread.is_alive():
        logger.info("[GoogleFitWorker] Background worker already running")
        return _worker_thread

    _worker_stop.clear()
    _worker_thread = threading.Thread(
        target=_worker_loop,
        name="google-fit-worker",
        daemon=True,
    )
    _worker_thread.start()
    return _worker_thread


def stop_google_fit_worker() -> None:
    global _worker_thread

    _worker_stop.set()
    thread = _worker_thread
    if thread and thread.is_alive():
        thread.join(timeout=3)
    _worker_thread = None
