from __future__ import annotations

from ..schemas import DialogueContext, MemorySnapshot


class EscalationDialogue:
    def compose(self, context: DialogueContext, snapshot: MemorySnapshot) -> str:
        risk = context.risk_level.lower()
        symptoms = {item.lower() for item in snapshot.symptom.active_symptoms}
        if risk in {"emergency", "critical"}:
            return "If this is happening now, please seek emergency care immediately."
        if risk == "high":
            if symptoms & {"chest pain", "shortness of breath", "palpitations", "dizziness"}:
                return "If the symptoms are worsening, happening at rest, or paired with breathlessness or fainting, urgent care today would be the safer move."
            return "If this is clearly worsening or feels severe, urgent in-person care today would be appropriate."
        return ""
