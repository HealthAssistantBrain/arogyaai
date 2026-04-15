"""Schedule the Google Fit background sync worker."""
from __future__ import annotations

import logging

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover - graceful fallback if dependency is unavailable
    BackgroundScheduler = None  # type: ignore[assignment]

from workers.google_fit_worker import run_google_fit_sync

logger = logging.getLogger("auto_fetch_scheduler")
_scheduler = None


def start_auto_fetch_scheduler():
    global _scheduler
    if BackgroundScheduler is None:
        logger.warning("[AutoFetch] APScheduler not installed; scheduler disabled.")
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_google_fit_sync,
        trigger="interval",
        minutes=5,
        id="google_fit_background_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("[AutoFetch] Scheduler started (5-minute Google Fit background sync)")
    return _scheduler


def stop_auto_fetch_scheduler():
    global _scheduler
    if _scheduler:
        try:
            if _scheduler.running:
                _scheduler.shutdown(wait=False)
        except Exception as exc:
            logger.warning("[AutoFetch] Scheduler shutdown failed: %s", exc)
        finally:
            _scheduler = None
