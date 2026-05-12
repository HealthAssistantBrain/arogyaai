from __future__ import annotations

from typing import Any

from ..schemas import MedicalTimelineEntry
from ..utils import safe_text, utc_now_iso


class InterventionTimelineBuilder:
    @staticmethod
    def build(intervention_analysis: dict[str, Any]) -> list[MedicalTimelineEntry]:
        timeline = []
        for index, item in enumerate(intervention_analysis.get("interventions") or []):
            timeline.append(
                MedicalTimelineEntry(
                    event_id=f"intervention_{index}",
                    event_type="intervention",
                    title=safe_text(item.get("title"), "Intervention"),
                    timestamp=utc_now_iso(),
                    severity="info",
                    narrative=safe_text(item.get("narrative"), "Intervention tracking note."),
                    clinical_impact="follow_up",
                    tags=["intervention", safe_text(item.get("category")).lower()],
                    evidence=[],
                )
            )
        return timeline[:10]
