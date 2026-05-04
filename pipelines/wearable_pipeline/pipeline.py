"""Google Fit wearable pipeline orchestration.

This module keeps the pipeline-level API thin and delegates provider details to
the backend GoogleFitService, which owns OAuth refresh, normalization, and DB
storage.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Awaitable, Callable

from database.session import SessionLocal
from models import User
from services.google_fit_service import GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS, GoogleFitService


FetchFunction = Callable[..., Awaitable[list[dict[str, Any]]]]


async def _fetch_metric_data(fetcher: FetchFunction, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return await fetcher(*args, **kwargs)


async def fetch_steps_data(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return await _fetch_metric_data(GoogleFitService.fetch_steps, *args, **kwargs)


async def fetch_heart_rate_data(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return await _fetch_metric_data(GoogleFitService.fetch_heart_rate, *args, **kwargs)


async def fetch_sleep_data(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return await _fetch_metric_data(GoogleFitService.fetch_sleep, *args, **kwargs)


async def fetch_spo2_data(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return await _fetch_metric_data(GoogleFitService.fetch_spo2, *args, **kwargs)


async def fetch_glucose_data(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return await _fetch_metric_data(GoogleFitService.fetch_glucose, *args, **kwargs)


async def fetch_blood_pressure_data(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return await _fetch_metric_data(GoogleFitService.fetch_blood_pressure, *args, **kwargs)


async def fetch_body_temperature_data(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return await _fetch_metric_data(GoogleFitService.fetch_body_temperature, *args, **kwargs)


async def fetch_location_data(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return await _fetch_metric_data(GoogleFitService.fetch_location, *args, **kwargs)


def run_wearable_pipeline(
    user_id: str,
    *,
    timezone_name: str | None = None,
    days: int = GOOGLE_FIT_DEFAULT_FETCH_WINDOW_DAYS,
) -> dict[str, Any]:
    db = SessionLocal()
    try:
        user_uuid = uuid.UUID(str(user_id))
        user = db.query(User).filter(User.id == user_uuid, User.is_deleted == False).first()
        if not user:
            return {
                "success": False,
                "status": "not_found",
                "error": "User not found",
                "user_id": user_id,
            }
        return asyncio.run(
            GoogleFitService.sync_steps_paginated(
                db,
                user,
                timezone_name=timezone_name,
                days=days,
            )
        )
    finally:
        db.close()
