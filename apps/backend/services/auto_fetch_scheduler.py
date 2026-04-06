"""
Auto-fetch scheduler for Google Fit vitals.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from database.session import SessionLocal
from models import User, UserSetting
from services.event_service import emit_event
from services.google_fit_service import GoogleFitService
from services.user_data_service import UserDataService

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover - graceful fallback if dependency is unavailable
    BackgroundScheduler = None  # type: ignore[assignment]

logger = logging.getLogger("auto_fetch_scheduler")
_scheduler = None


def _is_due(setting: UserSetting, now: datetime) -> bool:
    if not setting.auto_fetch_enabled:
        return False
    if not setting.last_fetch_at:
        return True
    elapsed = now - setting.last_fetch_at
    return elapsed.total_seconds() >= max(5, int(setting.fetch_interval_minutes)) * 60


async def _fetch_user_vitals(db, user: User):
    user_device = GoogleFitService._get_or_create_user_device(db, user)
    if not user_device:
        logger.info("[AutoFetch] Skipping user=%s because Google Fit is not connected", user.id)
        return

    access_token = await GoogleFitService.get_valid_access_token(db, user)
    if not access_token:
        logger.info("[AutoFetch] Skipping user=%s because Google Fit access token is unavailable", user.id)
        return

    records = []
    fetch_succeeded = False

    for fetcher in (
        GoogleFitService.fetch_heart_rate,
        GoogleFitService.fetch_steps,
        GoogleFitService.fetch_sleep,
        GoogleFitService.fetch_spo2,
    ):
        try:
            fetched = await fetcher(user, access_token)
            fetch_succeeded = True
            records.extend(fetched)
        except Exception as exc:  # keep the other metrics flowing
            logger.warning("[AutoFetch] %s failed for user=%s: %s", fetcher.__name__, user.id, exc)

    if not fetch_succeeded:
        db.rollback()
        logger.warning("[AutoFetch] No vitals were fetched for user=%s; last_fetch_at unchanged", user.id)
        return

    setting = UserDataService.get_or_create_settings(db, user)
    if records:
        saved_records = UserDataService.store_vitals(db, user, records)
        try:
            emit_event("VITALS_UPDATED", user.id, {"source": "google_fit", "records": len(saved_records)})
            for record in saved_records:
                vital_type = record.vital_type.value if getattr(record, "vital_type", None) else None
                if vital_type == "heart_rate" and record.value is not None:
                    emit_event("HEART_RATE_ALERT", user.id, {"heart_rate": record.value})
                elif vital_type == "steps" and record.value is not None:
                    emit_event("STEPS_MILESTONE", user.id, {"steps": record.value})
                elif vital_type == "sleep" and record.value is not None:
                    emit_event("SLEEP_ALERT", user.id, {"sleep": record.value})
        except Exception:
            logger.exception("[AutoFetch] Failed to emit notification events for user=%s", user.id)

    setting.last_fetch_at = datetime.now(timezone.utc)
    db.commit()


async def _tick_async():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        settings_rows = (
            db.query(UserSetting)
            .join(User, User.id == UserSetting.user_id)
            .filter(User.is_deleted == False, UserSetting.auto_fetch_enabled == True)
            .all()
        )

        for setting in settings_rows:
            if not _is_due(setting, now):
                continue
            user = setting.user
            if not user:
                continue
            try:
                await _fetch_user_vitals(db, user)
            except Exception as exc:
                logger.exception("[AutoFetch] Unexpected failure for user=%s: %s", user.id, exc)
    finally:
        db.close()


def run_auto_fetch_tick():
    asyncio.run(_tick_async())


def start_auto_fetch_scheduler():
    global _scheduler
    if BackgroundScheduler is None:
        logger.warning("[AutoFetch] APScheduler not installed; scheduler disabled.")
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_auto_fetch_tick,
        trigger="interval",
        minutes=5,
        id="google_fit_auto_fetch_tick",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("[AutoFetch] Scheduler started (5-minute global tick)")
    return _scheduler


def stop_auto_fetch_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
