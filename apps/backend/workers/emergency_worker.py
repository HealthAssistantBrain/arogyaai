from __future__ import annotations

import logging
import os
import threading
from typing import Any

from database.session import SessionLocal
from models import User
from services.emergency_engine.emergency_engine import detect_emergency

logger = logging.getLogger("emergency_worker")

_worker_thread: threading.Thread | None = None
_worker_stop = threading.Event()
_scan_lock = threading.Lock()


def _interval_seconds() -> int:
    raw = os.getenv("EMERGENCY_CHECK_INTERVAL_SECONDS", "60")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 60
    return max(60, min(300, value))


def _load_users(db) -> list[User]:
    return db.query(User).filter(User.is_deleted == False).all()


def run_emergency_detection_once() -> dict[str, Any]:
    if not _scan_lock.acquire(blocking=False):
        logger.info("[EmergencyWorker] Detection already running; skipping")
        return {"success": False, "status": "skipped", "message": "detection already running"}

    db = SessionLocal()
    try:
        users = _load_users(db)
        checked = 0
        emergencies = 0
        failed = 0

        for user in users:
            try:
                result = detect_emergency(user.id)
                checked += 1
                if result.get("data", {}).get("emergency"):
                    emergencies += 1
            except Exception as exc:
                failed += 1
                logger.exception("[EmergencyWorker] Detection failed user=%s: %s", user.id, exc)

        summary = {
            "success": failed == 0,
            "status": "ready" if failed == 0 else "partial",
            "checked_users": checked,
            "emergencies": emergencies,
            "failed_users": failed,
        }
        logger.info(
            "[EmergencyWorker] Scan complete | checked=%s emergencies=%s failed=%s",
            checked,
            emergencies,
            failed,
        )
        return summary
    finally:
        db.close()
        _scan_lock.release()


def _worker_loop() -> None:
    interval = _interval_seconds()
    logger.info("[EmergencyWorker] Background loop started | interval=%ss", interval)

    while not _worker_stop.is_set():
        try:
            run_emergency_detection_once()
        except Exception as exc:
            logger.exception("[EmergencyWorker] Background loop failed: %s", exc)

        if _worker_stop.wait(timeout=interval):
            break

    logger.info("[EmergencyWorker] Background loop stopped")


def start_emergency_worker() -> threading.Thread | None:
    global _worker_thread

    if _worker_thread and _worker_thread.is_alive():
        logger.info("[EmergencyWorker] Background worker already running")
        return _worker_thread

    _worker_stop.clear()
    _worker_thread = threading.Thread(target=_worker_loop, name="emergency-worker", daemon=True)
    _worker_thread.start()
    return _worker_thread


def stop_emergency_worker() -> None:
    global _worker_thread

    _worker_stop.set()
    thread = _worker_thread
    if thread and thread.is_alive():
        thread.join(timeout=3)
    _worker_thread = None
