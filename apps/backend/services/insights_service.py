from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models import User
from pipelines.ml_pipeline.service import MLPipelineService


class InsightsService:
    @staticmethod
    def get_insights(db: Session, user: User) -> dict[str, Any]:
        payload = MLPipelineService.predict(db, user, {"user_id": str(user.id), "data_points": {}})
        return {
            "success": True,
            "status": payload.get("status", "ready"),
            "source": payload.get("source", "db+rule_engine"),
            "error": payload.get("error"),
            "data": payload.get("data", {}),
            "last_updated": payload.get("last_updated"),
        }
