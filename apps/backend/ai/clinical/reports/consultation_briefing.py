from __future__ import annotations

from typing import Any

from ..utils import safe_text, structured_log, utc_now_iso


class ConsultationBriefingBuilder:
    @staticmethod
    def generate(bundle: dict[str, Any]) -> dict[str, Any]:
        patient = bundle.get("patient") if isinstance(bundle.get("patient"), dict) else {}
        consultation = bundle.get("consultation_preparation") if isinstance(bundle.get("consultation_preparation"), dict) else {}
        risk_summary = bundle.get("risk_summary") if isinstance(bundle.get("risk_summary"), dict) else {}
        structured_log(
            "[CONSULTATION_BRIEFING]",
            patient_id=safe_text(patient.get("id")),
            agenda_items=len(consultation.get("agenda") or []),
        )
        return {
            "patient_id": safe_text(patient.get("id")),
            "generated_at": utc_now_iso(),
            "title": f"Consultation briefing for {safe_text(patient.get('name'), 'patient')}",
            "headline": safe_text(consultation.get("headline")),
            "agenda": consultation.get("agenda") or [],
            "risk_headline": safe_text(risk_summary.get("headline")),
            "symptom_narrative": safe_text(consultation.get("symptom_narrative")),
            "follow_up_questions": consultation.get("follow_up_questions") or [],
        }
