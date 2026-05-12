from __future__ import annotations

from typing import Any

from ..schemas import RiskPriority
from ..utils import safe_text


class RiskSummaryEngine:
    @staticmethod
    def generate(
        context: dict[str, Any],
        patient_priority: dict[str, Any],
        deterioration_analysis: dict[str, Any],
        intervention_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        patient = context.get("patient") if isinstance(context.get("patient"), dict) else {}
        priorities = [RiskPriority.model_validate(item) for item in patient_priority.get("priorities") or []]
        headline = (
            f"Priority severity is {safe_text(patient_priority.get('severity'), 'moderate')} with an aggregate score of "
            f"{patient_priority.get('aggregate_score') or 0:.1f}."
        )
        summary = (
            f"Escalation candidate: {'yes' if patient_priority.get('escalation_candidate') else 'no'}. "
            f"Deterioration profile is {safe_text(deterioration_analysis.get('severity'), 'low')} and intervention response is "
            f"{safe_text(intervention_analysis.get('overall_status'), 'limited_data')}."
        )
        return {
            "patient_id": safe_text(patient.get("id")),
            "headline": headline,
            "summary": summary,
            "severity": safe_text(patient_priority.get("severity"), "moderate"),
            "aggregate_score": float(patient_priority.get("aggregate_score") or 0.0),
            "priorities": [item.model_dump(mode="json") for item in priorities],
            "escalation_candidate": bool(patient_priority.get("escalation_candidate")),
            "instability_clusters": patient_priority.get("instability_clusters") or [],
            "recovery_failure_pattern": bool(patient_priority.get("recovery_failure_pattern")),
        }
