from __future__ import annotations

from ..schemas import NarrativeContext


class BehavioralMemory:
    def build(self, context: NarrativeContext) -> dict[str, list[str]]:
        return {
            "carryover_recommendations": list(context.memory.get("recommendation_carryover") or []),
            "assistant_focus": list(context.memory.get("recent_assistant_focus") or []),
        }
