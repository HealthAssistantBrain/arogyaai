from __future__ import annotations

from ..schemas import DialogueContext, MemorySnapshot


class ReassuranceEngine:
    def compose(self, context: DialogueContext, snapshot: MemorySnapshot) -> str:
        emotion = str(context.emotional_context.get("dominant_emotion") or "").lower()
        risk = context.risk_level.lower()
        if risk in {"high", "critical", "emergency"}:
            return "I do not want to over-reassure this from chat alone."
        if emotion in {"anxiety", "anxious", "stressed", "worried"}:
            return "There is room to stay calm while we sort out what is most important."
        if snapshot.symptom.recovery_trajectory:
            return "It helps to compare this with the recent trajectory instead of reacting to one isolated moment."
        return "The safest approach is to stay measured and focus on the clearest next step."
