from __future__ import annotations

import asyncio
import logging
import random
import threading
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import joinedload

from database.session import SessionLocal
from models import GoogleFitConnection, User
from services.google_fit_service import GoogleFitService

logger = logging.getLogger("google_fit_worker")

_sync_lock = threading.Lock()
_worker_thread: threading.Thread | None = None
_worker_stop = threading.Event()

_MIN_INTERVAL_SECONDS = 180
_MAX_INTERVAL_SECONDS = 300


async def _sync_connected_user(db, user: User, connection: GoogleFitConnection | None) -> dict[str, Any]:
    timezone_name = connection.default_timezone if connection else None
    return await GoogleFitService.sync_steps(
        db,
        user,
        timezone_name=timezone_name,
        days=30,
        silent=True,
    )


def _load_connected_users(db) -> list[User]:
    return (
        db.query(User)
        .options(
            joinedload(User.google_fit_connection),
            joinedload(User.user_settings),
        )
        .join(GoogleFitConnection, GoogleFitConnection.user_id == User.id)
        .filter(User.is_deleted == False)
        .all()
    )


def run_google_fit_sync() -> dict[str, Any]:
    if not _sync_lock.acquire(blocking=False):
        logger.info("[GoogleFitWorker] Sync already running; skipping concurrent invocation")
        return {"success": False, "status": "skipped", "message": "sync already running"}

    db = SessionLocal()
    try:
        users = _load_connected_users(db)

        synced_users = 0
        skipped_users = 0
        failed_users = 0

        for user in users:
            setting = user.user_settings
            connection = user.google_fit_connection

            try:
                result = asyncio.run(_sync_connected_user(db, user, connection))
                if result.get("connected") and result.get("last_synced_at"):
                    if setting is not None:
                        setting.last_fetch_at = datetime.now(timezone.utc)
                        db.commit()
                    synced_users += 1
                else:
                    skipped_users += 1
            except Exception as exc:
                failed_users += 1
                db.rollback()
                logger.exception("[GoogleFitWorker] Sync failed for user=%s: %s", user.id, exc)

        summary = {
            "success": failed_users == 0,
            "status": "ready" if failed_users == 0 else "partial",
            "synced_users": synced_users,
            "skipped_users": skipped_users,
            "failed_users": failed_users,
        }
        logger.info(
            "[GoogleFitWorker] Sync finished | synced=%s skipped=%s failed=%s",
            synced_users,
            skipped_users,
            failed_users,
        )
        return summary
    finally:
        db.close()
        _sync_lock.release()


def _next_interval_seconds() -> int:
    return random.randint(_MIN_INTERVAL_SECONDS, _MAX_INTERVAL_SECONDS)


def _worker_loop() -> None:
    logger.info(
        "[GoogleFitWorker] Background loop started | interval=%ss-%ss",
        _MIN_INTERVAL_SECONDS,
        _MAX_INTERVAL_SECONDS,
    )

    while not _worker_stop.is_set():
        try:
            run_google_fit_sync()
        except Exception as exc:
            logger.exception("[GoogleFitWorker] Background sync loop failed: %s", exc)

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
