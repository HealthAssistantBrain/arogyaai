from __future__ import annotations

from typing import Any

from ..schemas import MedicalTimelineEntry, TimelineEvidence
from ..utils import evidence_from_event, safe_text


class DeteriorationTimelineBuilder:
    @staticmethod
    def build(events: list[dict[str, Any]], trend_analysis: dict[str, Any]) -> list[MedicalTimelineEntry]:
        deterioration = []
        for event in events:
            text = " ".join(
                [
                    safe_text(event.get("title")),
                    safe_text(event.get("description")),
                    safe_text(event.get("summary")),
                    safe_text(event.get("severity")),
                ]
            ).lower()
            if not any(token in text for token in ("alert", "elevated", "high", "critical", "worsen", "declin")):
                continue
            deterioration.append(
                MedicalTimelineEntry(
                    event_id=safe_text(event.get("id")),
                    event_type="deterioration",
                    title=safe_text(event.get("title"), "Deterioration signal"),
                    timestamp=safe_text(event.get("event_date") or event.get("timestamp")) or None,
                    severity=safe_text(event.get("severity")) or "warning",
                    narrative=safe_text(event.get("description") or event.get("summary"), "A deterioration signal was recorded."),
                    clinical_impact="watch_closely",
                    tags=["deterioration", safe_text(event.get("category") or event.get("type")).lower()],
                    evidence=[TimelineEvidence.model_validate(evidence_from_event(event))],
                )
            )
        for trend in (trend_analysis.get("deteriorating_metrics") or [])[:3]:
            deterioration.append(
                MedicalTimelineEntry(
                    event_id=f"trend_{safe_text(trend.get('metric'))}",
                    event_type="deterioration",
                    title=f"{safe_text(trend.get('label'), 'Metric')} drift",
                    timestamp=safe_text(trend.get("latest_timestamp")) or None,
                    severity="high",
                    narrative=safe_text(trend.get("narrative"), "A worsening physiologic trend was detected."),
                    clinical_impact="watch_closely",
                    tags=["trend", safe_text(trend.get("domain")).lower()],
                    evidence=[
                        TimelineEvidence(
                            reference_id=f"trend_{safe_text(trend.get('metric'))}",
                            title=safe_text(trend.get("label"), "Trend"),
                            source="wearable_compression",
                            timestamp=safe_text(trend.get("latest_timestamp")) or None,
                            excerpt=safe_text(trend.get("narrative")),
                        )
                    ],
                )
            )
        return deterioration[:12]
