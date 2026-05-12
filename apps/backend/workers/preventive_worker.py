from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from typing import Any

from sqlalchemy import exists, or_

from ai.prevention import PreventiveEngine
from ai.prevention.utils import safe_dict, safe_list
from database.session import log_pool_snapshot, session_scope
from models import HealthScoreRecord, LabResult, RiskScore, User, UserVital

logger = logging.getLogger("preventive_worker")

_worker_thread: threading.Thread | None = None
_worker_stop = threading.Event()
_scan_lock = threading.Lock()
_consecutive_worker_failures = 0


def _interval_seconds() -> int:
    raw = os.getenv("PREVENTIVE_MONITOR_INTERVAL_SECONDS", "180")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 180
    return max(120, min(900, value))


def _load_candidate_user_ids(db) -> list[str]:
    rows = (
        db.query(User.id)
        .filter(User.is_deleted == False)
        .filter(
            or_(
                exists().where(UserVital.user_id == User.id),
                exists().where(LabResult.user_id == User.id),
                exists().where(HealthScoreRecord.user_id == User.id),
                exists().where(RiskScore.user_id == User.id),
            )
        )
        .all()
    )
    return [str(user_id) for (user_id,) in rows]


def _load_user(db, user_id: str) -> User | None:
    try:
        user_uuid = uuid.UUID(str(user_id))
    except (TypeError, ValueError):
        return None
    return db.query(User).filter(User.id == user_uuid, User.is_deleted == False).first()


def run_preventive_monitoring_once(*, force_refresh: bool = False) -> dict[str, Any]:
    if not _scan_lock.acquire(blocking=False):
        logger.info("[PREVENTIVE_MONITOR] prevention cycle already running; skipping")
        return {"success": False, "status": "skipped", "message": "prevention cycle already running"}

    engine = PreventiveEngine()
    try:
        with session_scope(label="preventive_worker.load_users") as db:
            user_ids = _load_candidate_user_ids(db)

        logger.info("[PREVENTIVE_MONITOR] Autonomous prevention cycle start | users=%s", len(user_ids))

        processed = 0
        skipped = 0
        failed = 0
        alerts_generated = 0

        for user_id in user_ids:
            if _worker_stop.is_set():
                logger.info("[PREVENTIVE_MONITOR] Stop requested mid-cycle; ending current prevention cycle early")
                break

            try:
                with session_scope(label=f"preventive_worker.user:{user_id}") as user_db:
                    user = _load_user(user_db, user_id)
                    if user is None:
                        skipped += 1
                        logger.info("[PREVENTIVE_MONITOR] user missing during prevention scan | user_id=%s", user_id)
                        continue

                    payload = engine.generate(
                        user_db,
                        user,
                        force_refresh=force_refresh,
                        persist=True,
                    )
                    processed += 1
                    alerts_generated += len(safe_list(safe_dict(payload).get("alerts")))
                    logger.info(
                        "[RECOVERY_MONITOR] prevention refreshed | user_id=%s overall_risk=%.2f alerts=%s",
                        user_id,
                        float(safe_dict(safe_dict(payload).get("monitoring")).get("overall_risk") or 0.0),
                        len(safe_list(safe_dict(payload).get("alerts"))),
                    )
            except Exception as exc:
                failed += 1
                logger.exception("[PREVENTIVE_MONITOR] prevention scan failed user=%s error=%s", user_id, exc)

        summary = {
            "success": failed == 0,
            "status": "ready" if failed == 0 else "partial",
            "processed_users": processed,
            "skipped_users": skipped,
            "failed_users": failed,
            "alerts_generated": alerts_generated,
        }
        logger.info(
            "[PREVENTIVE_MONITOR] Autonomous prevention cycle complete | processed=%s skipped=%s failed=%s alerts=%s",
            processed,
            skipped,
            failed,
            alerts_generated,
        )
        log_pool_snapshot(force=failed > 0)
        return summary
    finally:
        _scan_lock.release()


def _worker_loop() -> None:
    global _consecutive_worker_failures
    logger.info("[PREVENTIVE_MONITOR] Background loop started | interval=%ss", _interval_seconds())

    while not _worker_stop.is_set():
        cycle_started_at = time.perf_counter()
        try:
            summary = run_preventive_monitoring_once(force_refresh=False)
            _consecutive_worker_failures = 0
            logger.info(
                "[PREVENTIVE_MONITOR] Cycle complete | status=%s processed=%s skipped=%s failed=%s duration_ms=%s",
                summary.get("status"),
                summary.get("processed_users", 0),
                summary.get("skipped_users", 0),
                summary.get("failed_users", 0),
                round((time.perf_counter() - cycle_started_at) * 1000, 2),
            )
        except Exception as exc:
            _consecutive_worker_failures += 1
            logger.exception("[PREVENTIVE_MONITOR] Background loop failed: %s", exc)
            backoff_seconds = min(900, _interval_seconds() * (2 ** min(_consecutive_worker_failures, 3)))
            logger.warning(
                "[PREVENTIVE_MONITOR] Applying backoff after failure | failures=%s backoff_seconds=%s",
                _consecutive_worker_failures,
                backoff_seconds,
            )
            if _worker_stop.wait(timeout=backoff_seconds):
                break
            continue

        if _worker_stop.wait(timeout=_interval_seconds()):
            break

    logger.info("[PREVENTIVE_MONITOR] Background loop stopped")


def start_preventive_worker() -> threading.Thread | None:
    global _worker_thread

    if _worker_thread and _worker_thread.is_alive():
        logger.info("[PREVENTIVE_MONITOR] Background worker already running")
        return _worker_thread

    _worker_stop.clear()
    _worker_thread = threading.Thread(target=_worker_loop, name="preventive-worker", daemon=True)
    _worker_thread.start()
    return _worker_thread


def stop_preventive_worker() -> None:
    global _worker_thread

    _worker_stop.set()
    thread = _worker_thread
    if thread and thread.is_alive():
        thread.join(timeout=3)
    _worker_thread = None
