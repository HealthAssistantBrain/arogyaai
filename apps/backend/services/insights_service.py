from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models import User
from pipelines.storage_pipeline.service import StoragePipelineService
from services.insight_formatter import sanitize_ai_insight_payload


class InsightsService:
    @staticmethod
    def _text(value: Any, fallback: str = "") -> str:
        if value is None:
            return fallback
        if isinstance(value, str):
            return value.strip() or fallback
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, dict):
            for key in ("title", "detail", "description", "message", "label", "text", "feature"):
                text = InsightsService._text(value.get(key))
                if text:
                    return text
        return fallback

    @staticmethod
    def _format_value(value: Any) -> str:
        if value is None:
            return "Actionable"
        if isinstance(value, (int, float)):
            return f"{value:.2f}".rstrip("0").rstrip(".")
        return InsightsService._text(value, "Actionable")

    @staticmethod
    def _build_dashboard_insights(payload: dict[str, Any] | None) -> list[dict[str, str]]:
        if not payload:
            return []

        drivers = payload.get("drivers") if isinstance(payload.get("drivers"), list) else []
        recommendations = payload.get("recommendations") if isinstance(payload.get("recommendations"), list) else []
        insights: list[dict[str, str]] = []

        for index, driver in enumerate(drivers[:3]):
            driver_payload = driver if isinstance(driver, dict) else {"label": driver}
            recommendation = recommendations[index] if index < len(recommendations) else None
            title = InsightsService._text(
                driver_payload.get("title")
                or driver_payload.get("label")
                or driver_payload.get("feature_name")
                or driver_payload.get("feature"),
                f"Health Signal {index + 1}",
            )
            description = InsightsService._text(
                driver_payload.get("detail")
                or driver_payload.get("description")
                or driver_payload.get("explanation"),
                "This signal contributed to your latest AI health assessment.",
            )

            insights.append(
                {
                    "title": title,
                    "value": InsightsService._format_value(
                        driver_payload.get("value")
                        or driver_payload.get("contribution")
                        or driver_payload.get("impact")
                    ),
                    "description": description,
                    "recommendation": InsightsService._text(
                        recommendation,
                        "Keep tracking this signal as more wearable and lab data arrives.",
                    ),
                }
            )

        if insights:
            return insights

        for index, recommendation in enumerate(recommendations[:3]):
            text = InsightsService._text(recommendation)
            if not text or text.lower() == "no data available yet":
                continue
            insights.append(
                {
                    "title": f"AI Recommendation {index + 1}",
                    "value": "Recommended",
                    "description": text,
                    "recommendation": text,
                }
            )

        return insights

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
                "explanation": sanitize_ai_insight_payload(stored.get("explanation")),
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
                    "insights": [],
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
                "insights": InsightsService._build_dashboard_insights(data),
                "recommendations": data.get("recommendations", []) if isinstance(data.get("recommendations"), list) else [],
                "availability": data.get("availability", {}) if isinstance(data.get("availability"), dict) else {},
                "clinical_history": data.get("clinical_history") if isinstance(data.get("clinical_history"), dict) else None,
            },
            "last_updated": data.get("last_updated"),
        }
