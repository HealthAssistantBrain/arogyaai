from __future__ import annotations

from typing import Any

from ..schemas import ProviderResponse, TimelineEvidence
from ..utils import dedupe_texts, safe_text, utc_now_iso


class ClinicianQueryEngine:
    QUERY_INTENTS = {
        "recent_change": ("what changed", "changed most recently", "recently"),
        "recovery_correlation": ("correlate", "recovery decline", "recovery"),
        "cardiovascular_deterioration": ("cardiovascular", "deterioration"),
        "anomaly_progression": ("anomaly progression", "anomaly timeline", "show anomaly"),
        "consultation_briefing": ("consultation", "briefing", "visit summary"),
    }

    @classmethod
    def detect_intent(cls, query: str) -> str:
        lowered = safe_text(query).lower()
        for intent, tokens in cls.QUERY_INTENTS.items():
            if all(token in lowered for token in tokens[:1]) and any(token in lowered for token in tokens):
                return intent
        if "anomaly" in lowered:
            return "anomaly_progression"
        if "cardio" in lowered or "heart" in lowered:
            return "cardiovascular_deterioration"
        if "recovery" in lowered:
            return "recovery_correlation"
        if "recent" in lowered or "changed" in lowered:
            return "recent_change"
        return "consultation_briefing"

    @staticmethod
    def answer(query: str, bundle: dict[str, Any], reasoning: str) -> ProviderResponse:
        patient = bundle.get("patient") if isinstance(bundle.get("patient"), dict) else {}
        timeline = bundle.get("medical_timeline") if isinstance(bundle.get("medical_timeline"), dict) else {}
        risk_summary = bundle.get("risk_summary") if isinstance(bundle.get("risk_summary"), dict) else {}
        consultation = bundle.get("consultation_preparation") if isinstance(bundle.get("consultation_preparation"), dict) else {}
        intent = ClinicianQueryEngine.detect_intent(query)
        if intent == "recent_change":
            answer = safe_text(timeline.get("recent_change_summary"), "No recent longitudinal changes were identified.")
            evidence_source = timeline.get("events") or []
        elif intent == "recovery_correlation":
            compression = bundle.get("physiological_compression") or []
            recovery_items = [
                safe_text(item.get("interpretation"))
                for item in compression
                if safe_text(item.get("state")).lower() == "deteriorating"
            ]
            answer = (
                "Recovery decline appears to track with "
                + ", ".join(dedupe_texts(recovery_items, limit=3))
                if recovery_items
                else "There is not enough signal compression to isolate the strongest recovery correlates."
            )
            evidence_source = timeline.get("deterioration_timeline") or []
        elif intent == "cardiovascular_deterioration":
            answer = safe_text(risk_summary.get("summary"), "No clear cardiovascular deterioration signal was isolated.")
            evidence_source = timeline.get("deterioration_timeline") or timeline.get("events") or []
        elif intent == "anomaly_progression":
            titles = dedupe_texts([item.get("title") for item in timeline.get("anomaly_timeline") or []], limit=5)
            answer = (
                f"Anomaly progression timeline includes: {', '.join(titles)}."
                if titles
                else "No anomaly progression events were available in the current timeline."
            )
            evidence_source = timeline.get("anomaly_timeline") or []
        else:
            answer = safe_text(consultation.get("headline") or risk_summary.get("headline"), "Consultation preparation is available but brief.")
            evidence_source = timeline.get("events") or []
        evidence = [
            TimelineEvidence.model_validate(item.get("evidence", [])[0])
            if isinstance(item, dict) and isinstance(item.get("evidence"), list) and item.get("evidence")
            else TimelineEvidence(reference_id=safe_text(item.get("event_id") or item.get("id")), title=safe_text(item.get("title"), "Evidence"), source="timeline")
            for item in evidence_source[:4]
        ]
        return ProviderResponse(
            patient_id=safe_text(patient.get("id")),
            generated_at=utc_now_iso(),
            query=query,
            intent=intent,
            answer=answer,
            reasoning=reasoning,
            confidence=0.74,
            grounded_evidence=evidence,
            follow_up_questions=consultation.get("follow_up_questions") or [],
            cards=[
                {
                    "title": safe_text(risk_summary.get("headline"), "Clinical priority"),
                    "description": safe_text(risk_summary.get("summary"), "Risk summary unavailable."),
                }
            ],
            escalation={},
            safety={},
        )
