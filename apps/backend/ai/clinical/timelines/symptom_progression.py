from __future__ import annotations

from typing import Any

from ..schemas import MedicalTimelineEntry, TimelineEvidence
from ..utils import evidence_from_event, safe_text


class SymptomProgressionBuilder:
    @staticmethod
    def build(events: list[dict[str, Any]]) -> list[MedicalTimelineEntry]:
        progression = []
        for event in events:
            category = safe_text(event.get("category") or event.get("type")).lower()
            if "symptom" not in category and "clinical history" not in safe_text(event.get("type")).lower():
                continue
            progression.append(
                MedicalTimelineEntry(
                    event_id=safe_text(event.get("id")),
                    event_type="symptom_progression",
                    title=safe_text(event.get("title"), "Symptom update"),
                    timestamp=safe_text(event.get("event_date") or event.get("timestamp")) or None,
                    severity=safe_text(event.get("severity")) or None,
                    narrative=safe_text(event.get("description") or event.get("summary"), "Symptom history recorded."),
                    clinical_impact="context",
                    tags=["symptom", safe_text(event.get("category")).lower()],
                    evidence=[TimelineEvidence.model_validate(evidence_from_event(event))],
                )
            )
        return progression[:10]
