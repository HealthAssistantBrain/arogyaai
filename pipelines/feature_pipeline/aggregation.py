from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from uuid import UUID

from sqlalchemy.orm import Session

from models import UserVital, UserVitalTypeEnum


def _window_start(days: int = 7) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=max(1, days))


def _recent_vital_rows(
    db: Session,
    user_id: UUID,
    vital_type: UserVitalTypeEnum,
    *,
    days: int = 7,
) -> list[UserVital]:
    return (
        db.query(UserVital)
        .filter(
            UserVital.user_id == user_id,
            UserVital.vital_type == vital_type,
            UserVital.timestamp >= _window_start(days),
        )
        .order_by(UserVital.timestamp.asc())
        .all()
    )


def _sleep_minutes_value(row: UserVital) -> float | None:
    if row.value is None:
        return None
    try:
        value = float(row.value)
    except (TypeError, ValueError):
        return None

    unit = str(row.unit or "").strip().lower()
    if unit in {"minutes", "minute", "min", "mins"}:
        return value
    if unit in {"hours", "hour", "hr", "hrs"}:
        return value * 60.0
    return value


def _daily_totals(rows: list[UserVital], *, sleep_minutes: bool = False, days: int = 7) -> list[float]:
    totals_by_day: dict[str, float] = {}
    for row in rows:
        if row.timestamp is None:
            continue
        if sleep_minutes:
            value = _sleep_minutes_value(row)
        else:
            try:
                value = float(row.value) if row.value is not None else None
            except (TypeError, ValueError):
                value = None
        if value is None:
            continue
        day_key = row.timestamp.astimezone(timezone.utc).date().isoformat()
        totals_by_day[day_key] = totals_by_day.get(day_key, 0.0) + value

    if not totals_by_day:
        return [0.0] * max(1, days)

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=max(1, days) - 1)
    series: list[float] = []
    cursor = start_date
    while cursor <= end_date:
        series.append(float(totals_by_day.get(cursor.isoformat(), 0.0)))
        cursor += timedelta(days=1)
    return series


def avg_steps_7d(db: Session, user_id: UUID) -> float:
    rows = _recent_vital_rows(db, user_id, UserVitalTypeEnum.STEPS, days=7)
    daily_totals = _daily_totals(rows, days=7)
    return round(float(mean(daily_totals)), 2) if daily_totals else 0.0


def hr_mean_7d(db: Session, user_id: UUID) -> float:
    rows = _recent_vital_rows(db, user_id, UserVitalTypeEnum.HEART_RATE, days=7)
    values: list[float] = []
    for row in rows:
        if row.value is None:
            continue
        try:
            values.append(float(row.value))
        except (TypeError, ValueError):
            continue
    return round(float(mean(values)), 2) if values else 0.0


def sleep_efficiency_7d(db: Session, user_id: UUID) -> float:
    rows = _recent_vital_rows(db, user_id, UserVitalTypeEnum.SLEEP, days=7)
    daily_sleep_minutes = _daily_totals(rows, sleep_minutes=True, days=7)
    if not any(value > 0 for value in daily_sleep_minutes):
        return 0.0
    average_minutes = float(mean(daily_sleep_minutes))
    efficiency = max(0.0, min((average_minutes / 480.0) * 100.0, 100.0))
    return round(efficiency, 2)


def data_availability_7d(db: Session, user_id: UUID) -> dict[str, bool]:
    step_rows = _recent_vital_rows(db, user_id, UserVitalTypeEnum.STEPS, days=7)
    heart_rows = _recent_vital_rows(db, user_id, UserVitalTypeEnum.HEART_RATE, days=7)
    sleep_rows = _recent_vital_rows(db, user_id, UserVitalTypeEnum.SLEEP, days=7)
    return {
        "steps": len(step_rows) > 0,
        "heart_rate": any((row.value or 0) > 0 for row in heart_rows),
        "sleep": any((_sleep_minutes_value(row) or 0) > 0 for row in sleep_rows),
    }
