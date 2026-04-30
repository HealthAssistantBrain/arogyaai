from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models import User
from pipelines.storage_pipeline.service import StoragePipelineService


class InsightsService:
    @staticmethod
    def get_insights(db: Session, user: User) -> dict[str, Any]:
        stored = StoragePipelineService.fetch_health_insights(db, user)
        if not stored:
            return {
                "success": True,
                "status": "insufficient_data",
                "source": "db",
                "error": None,
                "data": {
                    "risks": {},
                    "drivers": [],
                    "analysis": "",
                    "explanation": None,
                    "recommendations": ["No data available yet"],
                    "confidence": 0,
                    "data_points": 0,
                    "feature_snapshot": {},
                    "clinical_history": None,
                    "clinical_features": {},
                },
                "last_updated": None,
            }

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "risks": stored.get("risk", {}) if isinstance(stored.get("risk"), dict) else {},
                "drivers": stored.get("drivers", []) if isinstance(stored.get("drivers"), list) else [],
                "analysis": stored.get("analysis") or "",
                "explanation": stored.get("explanation") if isinstance(stored.get("explanation"), dict) else None,
                "recommendations": stored.get("recommendations", []) if isinstance(stored.get("recommendations"), list) else [],
                "confidence": stored.get("confidence") or 0,
                "data_points": stored.get("data_points") or 0,
                "feature_snapshot": stored.get("feature_snapshot", {}) if isinstance(stored.get("feature_snapshot"), dict) else {},
                "clinical_history": stored.get("clinical_history") if isinstance(stored.get("clinical_history"), dict) else None,
                "clinical_features": stored.get("clinical_features", {}) if isinstance(stored.get("clinical_features"), dict) else {},
            },
            "last_updated": stored.get("last_updated"),
        }

    @staticmethod
    def get_health_insights(db: Session, user: User) -> dict[str, Any]:
        data = StoragePipelineService.fetch_health_insights(db, user)
        if not data:
            return {
                "success": True,
                "status": "fallback",
                "source": "db",
                "error": None,
                "data": {
                    "risk_scores": {},
                    "drivers": [],
                    "recommendations": ["No data available yet"],
                    "availability": {
                        "has_wearable": False,
                        "has_lab": False,
                        "has_baseline": False,
                    },
                    "clinical_history": None,
                },
                "last_updated": None,
            }

        return {
            "success": True,
            "status": "ready",
            "source": "db",
            "error": None,
            "data": {
                "risk_scores": data.get("risk", {}) if isinstance(data.get("risk"), dict) else {},
                "drivers": data.get("drivers", []) if isinstance(data.get("drivers"), list) else [],
                "recommendations": data.get("recommendations", []) if isinstance(data.get("recommendations"), list) else [],
                "availability": data.get("availability", {}) if isinstance(data.get("availability"), dict) else {},
                "clinical_history": data.get("clinical_history") if isinstance(data.get("clinical_history"), dict) else None,
            },
            "last_updated": data.get("last_updated"),
        }
