from __future__ import annotations

from typing import Any

from ..utils import dedupe_texts, safe_text


class ConsultationSummaryBuilder:
    @staticmethod
    def generate(
        context: dict[str, Any],
        longitudinal_summary: dict[str, Any],
        risk_summary: dict[str, Any],
        intervention_analysis: dict[str, Any],
        medical_timeline: dict[str, Any],
    ) -> dict[str, Any]:
        patient = context.get("patient") if isinstance(context.get("patient"), dict) else {}
        agenda = dedupe_texts(
            [
                risk_summary.get("headline"),
                longitudinal_summary.get("summary_7d", {}).get("narrative"),
                intervention_analysis.get("headline"),
                medical_timeline.get("recent_change_summary"),
            ],
            limit=4,
        )
        questions = dedupe_texts(
            [
                "What changed most recently in symptoms or adherence?",
                "Which deterioration domains need targeted review today?",
                "Are current interventions producing meaningful stabilization?",
                "Should the escalation threshold change before the next review?",
            ],
            limit=4,
        )
        symptom_narrative = safe_text(
            longitudinal_summary.get("deterioration_summary", {}).get("narrative")
            or medical_timeline.get("recent_change_summary"),
            "No recent symptom narrative was available.",
        )
        return {
            "patient_id": safe_text(patient.get("id")),
            "headline": f"Consultation preparation for {safe_text(patient.get('name'), 'patient')}",
            "agenda": agenda,
            "symptom_narrative": symptom_narrative,
            "trend_overview": safe_text(longitudinal_summary.get("summary_30d", {}).get("narrative")),
            "intervention_outcomes": intervention_analysis.get("interventions") or [],
            "follow_up_questions": questions,
        }
