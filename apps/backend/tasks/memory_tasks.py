from __future__ import annotations

import asyncio

from ai.memory.memory_decay import run_decay_cycle_sync
from ai.memory.memory_engine import get_memory_engine
from core.celery_app import celery_app
from database.session import SessionLocal
from models import User


@celery_app.task(name="memory.nightly_decay", queue="maintenance")
def run_nightly_decay():
    return run_decay_cycle_sync(SessionLocal)


@celery_app.task(name="memory.weekly_summarize", queue="maintenance")
def run_weekly_summarization():
    async def _run():
        memory = get_memory_engine()
        db = SessionLocal()
        try:
            user_ids = [str(row[0]) for row in db.query(User.id).all()]
        finally:
            db.close()
        await memory.warmup()
        for user_id in user_ids:
            await memory._summarizer.summarize_if_needed(user_id)
        return {"users_checked": len(user_ids)}

    return asyncio.run(_run())
