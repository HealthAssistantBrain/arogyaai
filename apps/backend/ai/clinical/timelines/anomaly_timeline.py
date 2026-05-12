from __future__ import annotations

from typing import Any

from ..schemas import MedicalTimelineEntry, TimelineEvidence
from ..utils import event_severity_rank, evidence_from_event, safe_text


class AnomalyTimelineBuilder:
    @staticmethod
    def build(events: list[dict[str, Any]]) -> list[MedicalTimelineEntry]:
        anomalies = []
        for event in events:
            title = safe_text(event.get("title"))
            description = safe_text(event.get("description") or event.get("summary"))
            category = safe_text(event.get("category") or event.get("type")).lower()
            if event_severity_rank(event.get("severity")) < 2 and "alert" not in category and "abnormal" not in description.lower():
                continue
            anomalies.append(
                MedicalTimelineEntry(
                    event_id=safe_text(event.get("id")),
                    event_type="anomaly",
                    title=title or "Anomaly detected",
                    timestamp=safe_text(event.get("event_date") or event.get("timestamp")) or None,
                    severity=safe_text(event.get("severity")) or "warning",
                    narrative=description or "A clinically relevant anomaly was registered in the timeline.",
                    clinical_impact="surveillance",
                    tags=["anomaly", category or "clinical"],
                    evidence=[TimelineEvidence.model_validate(evidence_from_event(event))],
                )
            )
        return anomalies[:12]
