from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from models import HealthMemoryRecord, User


class DeteriorationHistory:
    @staticmethod
    def load(db: Session, user: User, *, days: int = 30, limit: int = 18) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
        rows = (
            db.query(HealthMemoryRecord)
            .filter(
                HealthMemoryRecord.user_id == user.id,
                HealthMemoryRecord.metric_name.like("preventive:signal:%"),
                HealthMemoryRecord.created_at >= since,
            )
            .order_by(HealthMemoryRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "metric_name": row.metric_name,
                "metric_value": float(row.metric_value) if row.metric_value is not None else None,
                "summary": row.trend_note,
                "direction": row.trend_direction,
                "risk_level": row.risk_level,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
