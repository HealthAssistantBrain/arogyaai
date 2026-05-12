from __future__ import annotations

from ..schemas import DialogueContext, MemorySnapshot


class EmotionalCalibration:
    def calibrate(self, context: DialogueContext, snapshot: MemorySnapshot) -> dict[str, str]:
        dominant = str(context.emotional_context.get("dominant_emotion") or snapshot.behavioral.user_state or "neutral").lower()
        if dominant in {"anxiety", "anxious", "stressed", "worried"}:
            return {"tone": "steady", "reassurance": "moderate", "pace": "stepwise"}
        if dominant in {"confusion", "confused", "overwhelmed"}:
            return {"tone": "clear", "reassurance": "light", "pace": "slower"}
        if dominant in {"frustration", "frustrated"}:
            return {"tone": "direct", "reassurance": "light", "pace": "efficient"}
        return {"tone": "calm", "reassurance": "light", "pace": "steady"}
