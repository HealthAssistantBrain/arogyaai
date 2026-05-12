from __future__ import annotations

from typing import Any

from ..schemas import MedicalTimeline, MedicalTimelineEntry, TimelineEvidence
from ..utils import evidence_from_event, safe_text, sort_events, structured_log, utc_now_iso
from .anomaly_timeline import AnomalyTimelineBuilder
from .deterioration_timeline import DeteriorationTimelineBuilder
from .intervention_timeline import InterventionTimelineBuilder
from .symptom_progression import SymptomProgressionBuilder


class MedicalTimelineEngine:
    @staticmethod
    def _normalize_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for event in sort_events(events):
            title = safe_text(event.get("title"), "Clinical event")
            description = safe_text(event.get("description") or event.get("summary"), "Clinical event captured in the longitudinal record.")
            normalized.append(
                {
                    **event,
                    "title": title,
                    "description": description,
                    "event_date": safe_text(event.get("event_date") or event.get("timestamp")) or None,
                }
            )
        return normalized

    @staticmethod
    def generate(
        context: dict[str, Any],
        trend_analysis: dict[str, Any],
        intervention_analysis: dict[str, Any],
    ) -> MedicalTimeline:
        patient = context.get("patient") if isinstance(context.get("patient"), dict) else {}
        source_events = context.get("history") if isinstance(context.get("history"), list) else []
        events = MedicalTimelineEngine._normalize_events(source_events)
        entries = [
            MedicalTimelineEntry(
                event_id=safe_text(event.get("id")),
                event_type=safe_text(event.get("event_type") or event.get("type"), "clinical_event"),
                title=safe_text(event.get("title"), "Clinical event"),
                timestamp=safe_text(event.get("event_date") or event.get("timestamp")) or None,
                severity=safe_text(event.get("severity")) or None,
                narrative=safe_text(event.get("description") or event.get("summary")),
                clinical_impact="context",
                tags=[safe_text(event.get("category") or event.get("type")).lower()],
                evidence=[TimelineEvidence.model_validate(evidence_from_event(event))],
            )
            for event in events
        ]
        anomaly_timeline = AnomalyTimelineBuilder.build(events)
        deterioration_timeline = DeteriorationTimelineBuilder.build(events, trend_analysis)
        intervention_timeline = InterventionTimelineBuilder.build(intervention_analysis)
        symptom_progression = SymptomProgressionBuilder.build(events)
        recent_changes = [entry.title for entry in entries[-3:]] if entries else []
        narrative = (
            f"The longitudinal timeline currently contains {len(entries)} clinically relevant events with "
            f"{len(anomaly_timeline)} anomaly signals and {len(deterioration_timeline)} deterioration markers."
        )
        recent_change_summary = (
            f"Most recent changes: {', '.join(recent_changes)}."
            if recent_changes
            else "No recent timeline changes were available."
        )
        structured_log(
            "[MEDICAL_TIMELINE]",
            patient_id=safe_text(patient.get("id")),
            events=len(entries),
            anomalies=len(anomaly_timeline),
        )
        return MedicalTimeline(
            patient_id=safe_text(patient.get("id")),
            generated_at=utc_now_iso(),
            narrative=narrative,
            recent_change_summary=recent_change_summary,
            events=entries[-20:],
            anomaly_timeline=anomaly_timeline,
            deterioration_timeline=deterioration_timeline,
            intervention_timeline=intervention_timeline,
            symptom_progression=symptom_progression,
            metadata={
                "source_event_count": len(events),
                "anomaly_count": len(anomaly_timeline),
                "deterioration_count": len(deterioration_timeline),
            },
        )
