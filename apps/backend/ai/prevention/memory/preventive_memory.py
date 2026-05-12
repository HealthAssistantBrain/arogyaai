from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from sqlalchemy.orm import Session

from models import HealthMemoryRecord, HealthScoreRecord, RiskScore, User
from ..utils import clamp, priority_from_score, safe_dict, safe_list, safe_text

logger = logging.getLogger("uvicorn.error")


class PreventiveMemory:
    DEDUPE_WINDOW = timedelta(hours=6)

    @staticmethod
    def load(db: Session, user: User, *, days: int = 30, limit: int = 24) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
        rows = (
            db.query(HealthMemoryRecord)
            .filter(
                HealthMemoryRecord.user_id == user.id,
                HealthMemoryRecord.metric_name.like("preventive:%"),
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
                "trend_note": row.trend_note,
                "trend_direction": row.trend_direction,
                "risk_level": row.risk_level,
                "importance": row.importance,
                "tags": row.tags or [],
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    @staticmethod
    def _is_duplicate(db: Session, user: User, metric_name: str, trend_note: str) -> bool:
        threshold = datetime.now(timezone.utc) - PreventiveMemory.DEDUPE_WINDOW
        existing = (
            db.query(HealthMemoryRecord)
            .filter(
                HealthMemoryRecord.user_id == user.id,
                HealthMemoryRecord.metric_name == metric_name,
                HealthMemoryRecord.created_at >= threshold,
            )
            .order_by(HealthMemoryRecord.created_at.desc())
            .first()
        )
        if existing is None:
            return False
        return safe_text(existing.trend_note) == safe_text(trend_note)

    @staticmethod
    def _attach_payload_cache(
        payload: dict[str, Any],
        *,
        latest_health_score: HealthScoreRecord | None,
        latest_risk_score: RiskScore | None,
    ) -> None:
        payload_copy = deepcopy(payload)
        if latest_health_score is not None:
            health_payload = dict(latest_health_score.health_payload or {})
            health_payload["prevention"] = payload_copy
            latest_health_score.health_payload = health_payload
        if latest_risk_score is not None:
            risk_payload = dict(latest_risk_score.risk_payload or {})
            health_insights = safe_dict(risk_payload.get("health_insights"))
            health_insights["prevention"] = payload_copy
            risk_payload["health_insights"] = health_insights
            risk_payload["prevention"] = payload_copy
            latest_risk_score.risk_payload = risk_payload

    @staticmethod
    def persist(
        db: Session,
        user: User,
        *,
        payload: dict[str, Any],
        latest_health_score: HealthScoreRecord | None = None,
        latest_risk_score: RiskScore | None = None,
    ) -> None:
        PreventiveMemory._attach_payload_cache(
            payload,
            latest_health_score=latest_health_score,
            latest_risk_score=latest_risk_score,
        )

        generated_at = datetime.now(timezone.utc)
        for signal in safe_list(payload.get("signals"))[:8]:
            signal_payload = safe_dict(signal)
            metric_name = f"preventive:signal:{safe_text(signal_payload.get('domain'), 'general')}"
            trend_note = safe_text(signal_payload.get("summary"))
            if not trend_note or PreventiveMemory._is_duplicate(db, user, metric_name, trend_note):
                continue
            risk_score = float(signal_payload.get("risk_score") or 0.0)
            db.add(
                HealthMemoryRecord(
                    user_id=user.id,
                    metric_name=metric_name,
                    metric_value=risk_score,
                    metric_unit="risk",
                    trend_direction=safe_text(signal_payload.get("direction"), "stable"),
                    trend_note=trend_note[:500],
                    disease_context=safe_text(signal_payload.get("domain"), "preventive"),
                    source="preventive_engine",
                    risk_level=priority_from_score(risk_score),
                    importance="high" if risk_score >= 75.0 else "medium",
                    decay_score=1.0,
                    tags=safe_list(signal_payload.get("tags"))[:6],
                    created_at=generated_at,
                )
            )

        plan = safe_dict(payload.get("intervention_plan"))
        for action in safe_list(plan.get("priorities"))[:5]:
            action_payload = safe_dict(action)
            metric_name = f"preventive:intervention:{safe_text(action_payload.get('action_id'), 'general')}"
            trend_note = safe_text(action_payload.get("detail") or action_payload.get("title"))
            if not trend_note or PreventiveMemory._is_duplicate(db, user, metric_name, trend_note):
                continue
            impact = clamp(float(action_payload.get("expected_impact") or 0.0))
            db.add(
                HealthMemoryRecord(
                    user_id=user.id,
                    metric_name=metric_name,
                    metric_value=impact,
                    metric_unit="impact",
                    trend_direction="supportive",
                    trend_note=trend_note[:500],
                    disease_context="prevention",
                    source="preventive_engine",
                    risk_level=safe_text(action_payload.get("priority"), "medium"),
                    importance="high" if safe_text(action_payload.get("priority"), "medium") == "high" else "medium",
                    decay_score=1.0,
                    tags=safe_list(action_payload.get("domains"))[:6],
                    created_at=generated_at,
                )
            )

        logger.info(
            "[PREVENTIVE_MONITOR] persisted preventive memory user_id=%s signals=%s actions=%s",
            str(user.id),
            len(safe_list(payload.get("signals"))),
            len(safe_list(plan.get("priorities"))),
        )
        db.commit()
