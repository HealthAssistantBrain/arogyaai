from __future__ import annotations

from ..schemas import NarrativeContext


class SymptomMemory:
    def build(self, context: NarrativeContext) -> dict[str, list[str]]:
        return {
            "ongoing_symptoms": list(context.memory.get("ongoing_symptoms") or []),
            "active_symptoms": list(context.symptoms or []),
        }
