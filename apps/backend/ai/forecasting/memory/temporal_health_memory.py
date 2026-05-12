from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models import HealthMemoryRecord, User


class TemporalHealthMemory:
    @staticmethod
    def recent_context(db: Session, user: User, *, days: int = 21, limit: int = 8) -> list[str]:
        since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
        rows = (
            db.query(HealthMemoryRecord)
            .filter(HealthMemoryRecord.user_id == user.id, HealthMemoryRecord.created_at >= since)
            .order_by(HealthMemoryRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        summary: list[str] = []
        for row in rows:
            metric = str(row.metric_name or "").replace("_", " ")
            note = str(row.trend_note or "").strip()
            if metric.startswith("forecast:"):
                metric = metric.replace("forecast:", "").replace(":", " ")
            sentence = f"{metric.title()}: {note or row.trend_direction or 'stable'}"
            summary.append(sentence.strip())
        return summary
