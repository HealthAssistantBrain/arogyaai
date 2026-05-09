from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

from database.session import log_pool_snapshot, session_scope
from models import User
from services.emergency_engine.emergency_engine import detect_emergency

logger = logging.getLogger("emergency_worker")

_worker_thread: threading.Thread | None = None
_worker_stop = threading.Event()
_scan_lock = threading.Lock()
_consecutive_worker_failures = 0


def _interval_seconds() -> int:
    raw = os.getenv("EMERGENCY_CHECK_INTERVAL_SECONDS", "60")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 60
    return max(60, min(300, value))


def _load_user_ids(db) -> list[str]:
    return [str(user_id) for (user_id,) in db.query(User.id).filter(User.is_deleted == False).all()]


def run_emergency_detection_once() -> dict[str, Any]:
    if not _scan_lock.acquire(blocking=False):
        logger.info("[EmergencyWorker] Detection already running; skipping")
        return {"success": False, "status": "skipped", "message": "detection already running"}

    try:
        with session_scope(label="emergency_worker.load_users") as db:
            user_ids = _load_user_ids(db)

        checked = 0
        emergencies = 0
        failed = 0

        for user_id in user_ids:
            if _worker_stop.is_set():
                logger.info("[EmergencyWorker] Stop requested mid-scan; ending current cycle early")
                break
            try:
                with session_scope(label=f"emergency_worker.detect:{user_id}") as user_db:
                    result = detect_emergency(user_id, db=user_db)
                checked += 1
                if result.get("data", {}).get("emergency"):
                    emergencies += 1
            except Exception as exc:
                failed += 1
                logger.exception("[EmergencyWorker] Detection failed user=%s: %s", user_id, exc)

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
        log_pool_snapshot(force=failed > 0)
        return summary
    finally:
        _scan_lock.release()


def _worker_loop() -> None:
    global _consecutive_worker_failures
    logger.info("[EmergencyWorker] Background loop started | interval=%ss", _interval_seconds())

    while not _worker_stop.is_set():
        cycle_started_at = time.perf_counter()
        try:
            summary = run_emergency_detection_once()
            _consecutive_worker_failures = 0
            logger.info(
                "[EmergencyWorker] Cycle complete | status=%s checked=%s emergencies=%s failed=%s duration_ms=%s",
                summary.get("status"),
                summary.get("checked_users", 0),
                summary.get("emergencies", 0),
                summary.get("failed_users", 0),
                round((time.perf_counter() - cycle_started_at) * 1000, 2),
            )
        except Exception as exc:
            _consecutive_worker_failures += 1
            logger.exception("[EmergencyWorker] Background loop failed: %s", exc)
            backoff_seconds = min(300, _interval_seconds() * (2 ** min(_consecutive_worker_failures, 3)))
            logger.warning(
                "[EmergencyWorker] Applying backoff after failure | failures=%s backoff_seconds=%s",
                _consecutive_worker_failures,
                backoff_seconds,
            )
            if _worker_stop.wait(timeout=backoff_seconds):
                break
            continue

        if _worker_stop.wait(timeout=_interval_seconds()):
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
