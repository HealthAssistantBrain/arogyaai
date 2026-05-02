from __future__ import annotations

from typing import Any

from core.celery_app import celery_app
from services.emergency_engine.emergency_engine import detect_emergency
from workers.emergency_worker import run_emergency_detection_once


@celery_app.task(name="workers.emergency_tasks.check_emergency_for_user", queue="emergency")
def check_emergency_for_user_task(user_id: str) -> dict[str, Any]:
    return detect_emergency(user_id)


@celery_app.task(name="workers.emergency_tasks.scan_emergencies", queue="emergency")
def scan_emergencies_task() -> dict[str, Any]:
    return run_emergency_detection_once()
