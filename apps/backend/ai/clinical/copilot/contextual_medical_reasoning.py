from __future__ import annotations

from typing import Any

from ..utils import dedupe_texts, safe_text


class ContextualMedicalReasoning:
    @staticmethod
    def build(intent: str, bundle: dict[str, Any]) -> str:
        summary = bundle.get("summary") if isinstance(bundle.get("summary"), dict) else {}
        risk_summary = bundle.get("risk_summary") if isinstance(bundle.get("risk_summary"), dict) else {}
        timeline = bundle.get("medical_timeline") if isinstance(bundle.get("medical_timeline"), dict) else {}
        consultation = bundle.get("consultation_preparation") if isinstance(bundle.get("consultation_preparation"), dict) else {}
        fragments = {
            "recent_change": timeline.get("recent_change_summary"),
            "recovery_correlation": "Recovery decline appears most aligned with sleep, activity, and cardiovascular drift when those signals trend together.",
            "cardiovascular_deterioration": risk_summary.get("summary"),
            "anomaly_progression": timeline.get("narrative"),
            "consultation_briefing": consultation.get("headline"),
        }
        return dedupe_texts(
            [
                fragments.get(intent),
                summary.get("overview"),
                risk_summary.get("headline"),
            ],
            limit=3,
        )[0]
