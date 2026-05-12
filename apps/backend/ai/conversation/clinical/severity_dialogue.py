from __future__ import annotations

from ..schemas import DialogueContext, MemorySnapshot


class SeverityDialogue:
    def describe(self, context: DialogueContext, snapshot: MemorySnapshot) -> str:
        risk = context.risk_level.lower()
        symptoms = ", ".join(snapshot.symptom.active_symptoms[:2]).lower()
        if risk in {"emergency", "critical"}:
            return "This needs urgent in-person assessment rather than watchful waiting."
        if risk == "high":
            return "This deserves prompt clinical attention, especially if it is intensifying."
        if risk == "medium":
            if symptoms:
                return f"This looks clinically meaningful enough to follow closely, particularly around the {symptoms} pattern."
            return "This looks clinically meaningful enough to follow closely."
        if snapshot.symptom.baseline_signals:
            return "The pattern is not automatically dangerous, but it is different enough from baseline to pay attention to."
        return "This sounds more watchful than immediately dangerous, but it still deserves a careful read."
