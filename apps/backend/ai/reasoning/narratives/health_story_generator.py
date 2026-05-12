from __future__ import annotations

from typing import Any

from ..schemas import NarrativeContext, ReasoningCard


class HealthStoryGenerator:
    def generate(
        self,
        context: NarrativeContext,
        *,
        narrative: str,
        temporal: dict[str, Any],
        cards: list[ReasoningCard],
    ) -> dict[str, Any]:
        return {
            "past": list(context.memory.get("major_trends") or [])[:2],
            "present": [card.summary for card in cards[:3]],
            "next": list((temporal.get("forecast_summaries") or {}).values())[:2],
            "narrative": narrative,
        }
