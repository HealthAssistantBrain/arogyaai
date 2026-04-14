from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models import User
from services.feature_service import FeatureService
from services.risk_engine import RiskEngine


class InsightsService:
    @staticmethod
    def get_insights(db: Session, user: User) -> dict[str, Any]:
        features = FeatureService.build_feature_snapshot(db, user)
        payload = RiskEngine.evaluate(features, user_id=str(user.id))

        return {
            "success": True,
            "status": payload.get("status", "ready"),
            "source": "db+rule_engine",
            "error": None,
            "data": payload,
            "last_updated": payload.get("last_updated"),
        }
