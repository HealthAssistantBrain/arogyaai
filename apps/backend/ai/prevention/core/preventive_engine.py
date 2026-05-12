from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ai.forecasting import PredictiveForecastingEngine
from models import HealthScoreRecord, LabResult, RiskScore, User, UserVital

from ..memory import DeteriorationHistory, InterventionHistory, PreventiveMemory
from ..utils import safe_dict, utc_now
from .preventive_pipeline import PreventivePipeline

logger = logging.getLogger("uvicorn.error")


class PreventiveEngine:
    STALENESS_WINDOW_MINUTES = 20

    def __init__(self) -> None:
        self.forecasting_engine = PredictiveForecastingEngine()
        self.pipeline = PreventivePipeline()

    @staticmethod
    def _latest_dependency_timestamp(db: Session, user: User) -> datetime | None:
        timestamps: list[datetime] = []
        for model, column in (
            (UserVital, UserVital.timestamp),
            (LabResult, LabResult.timestamp),
            (HealthScoreRecord, HealthScoreRecord.calculated_at),
            (RiskScore, RiskScore.calculated_at),
        ):
            row = (
                db.query(model)
                .filter(model.user_id == user.id)
                .order_by(desc(column))
                .first()
            )
            if row is not None and getattr(row, column.key, None) is not None:
                timestamps.append(getattr(row, column.key))
        return max(timestamps, default=None)

    def _build_context(self, db: Session, user: User) -> dict[str, Any]:
        context = self.forecasting_engine._build_context(db, user)
        context["forecasting"] = self.forecasting_engine.generate(db, user, persist=False)
        context["preventive_history"] = PreventiveMemory.load(db, user)
        context["intervention_history"] = InterventionHistory.load(db, user)
        context["deterioration_history"] = DeteriorationHistory.load(db, user)
        return context

    def _should_use_cache(self, context: dict[str, Any], dependency_at: datetime | None) -> dict[str, Any] | None:
        latest_health = safe_dict(context.get("latest_health_payload"))
        existing = safe_dict(latest_health.get("prevention"))
        generated_at_raw = existing.get("generated_at")
        if not generated_at_raw:
            return None
        try:
            generated_at = datetime.fromisoformat(str(generated_at_raw).replace("Z", "+00:00"))
        except ValueError:
            return None
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        if generated_at < (utc_now() - timedelta(minutes=self.STALENESS_WINDOW_MINUTES)):
            return None
        if dependency_at is not None and dependency_at > generated_at:
            return None
        return existing

    def generate(
        self,
        db: Session,
        user: User,
        *,
        force_refresh: bool = False,
        persist: bool = True,
    ) -> dict[str, Any]:
        context = self._build_context(db, user)
        dependency_at = self._latest_dependency_timestamp(db, user)
        if not force_refresh:
            cached = self._should_use_cache(context, dependency_at)
            if cached:
                return cached

        payload = self.pipeline.run(user_id=str(user.id), context=context)
        payload["generated_at"] = utc_now().isoformat()
        payload["status"] = "ready"
        payload["source"] = "preventive_engine"
        if persist:
            PreventiveMemory.persist(
                db,
                user,
                payload=payload,
                latest_health_score=context.get("latest_health_score"),
                latest_risk_score=context.get("latest_risk_score"),
            )
        logger.info(
            "[PREVENTIVE_ALERT] user_id=%s overall_risk=%.2f top_alerts=%s",
            str(user.id),
            float(safe_dict(payload.get("monitoring")).get("overall_risk") or 0.0),
            len(payload.get("alerts") or []),
        )
        return payload

    def generate_for_context(self, *, user_id: str, context: dict[str, Any]) -> dict[str, Any]:
        payload = self.pipeline.run(user_id=user_id, context=context)
        payload["generated_at"] = utc_now().isoformat()
        payload["status"] = "ready"
        payload["source"] = "preventive_engine"
        return payload
