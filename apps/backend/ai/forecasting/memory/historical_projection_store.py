from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from models import HealthMemoryRecord, HealthScoreRecord, RiskScore, User


class HistoricalProjectionStore:
    @staticmethod
    def persist(
        db: Session,
        user: User,
        *,
        forecast_payload: dict[str, Any],
        latest_health_score: HealthScoreRecord | None,
        latest_risk_score: RiskScore | None,
    ) -> None:
        payload_copy = deepcopy(forecast_payload)
        if latest_health_score is not None:
            health_payload = dict(latest_health_score.health_payload or {})
            health_payload["forecasting"] = payload_copy
            latest_health_score.health_payload = health_payload
        if latest_risk_score is not None:
            risk_payload = dict(latest_risk_score.risk_payload or {})
            risk_payload["forecasting"] = payload_copy
            history = risk_payload.get("forecast_history") if isinstance(risk_payload.get("forecast_history"), list) else []
            history = [*history[-11:], {"generated_at": payload_copy.get("generated_at"), "summary": payload_copy.get("summary"), "confidence": payload_copy.get("confidence")}]
            risk_payload["forecast_history"] = history
            latest_risk_score.risk_payload = risk_payload

        generated_at = datetime.now(timezone.utc)
        for window, bundle in (forecast_payload.get("forecast") or {}).items():
            if not isinstance(bundle, dict):
                continue
            for item in bundle.get("domains", []) + bundle.get("predictions", []):
                if not isinstance(item, dict):
                    continue
                projected_risk = float(item.get("projected_risk") or 0.0)
                risk_level = "high" if projected_risk >= 60 else "moderate" if projected_risk >= 40 else "low"
                db.add(
                    HealthMemoryRecord(
                        user_id=user.id,
                        metric_name=f"forecast:{window}:{item.get('domain')}",
                        metric_value=projected_risk,
                        metric_unit="risk",
                        trend_direction=str(item.get("direction") or "stable"),
                        trend_note=str(item.get("explanation") or "")[:500],
                        disease_context=str(item.get("domain") or "forecasting"),
                        source="forecasting_engine",
                        risk_level=risk_level,
                        importance="high" if projected_risk >= 60 else "medium",
                        decay_score=1.0,
                        tags=["forecast", str(window), str(item.get("domain") or "general")],
                        created_at=generated_at,
                    )
                )
        db.commit()
