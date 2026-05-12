from __future__ import annotations

from ..schemas import DialogueContext, MemorySnapshot


class AdaptiveQuestioning:
    def determine_gaps(self, context: DialogueContext, snapshot: MemorySnapshot) -> list[str]:
        query = context.query.lower()
        gaps: list[str] = []
        if snapshot.symptom.active_symptoms and not any(token in query for token in ("since", "started", "days", "weeks", "hours")):
            gaps.append("timecourse")
        if snapshot.symptom.active_symptoms and not any(token in query for token in ("worse", "better", "same", "improving")):
            gaps.append("trend")
        if any(symptom.lower() in {"chest pain", "palpitations", "shortness of breath", "dizziness"} for symptom in snapshot.symptom.active_symptoms):
            if not any(token in query for token in ("faint", "breath", "sweat", "jaw", "arm")):
                gaps.append("red_flags")
        if snapshot.symptom.baseline_signals and not any(token in query for token in ("rest", "baseline", "usual", "normal")):
            gaps.append("baseline")
        if context.risk_level.lower() in {"high", "critical", "emergency"}:
            gaps = ["red_flags"] + [item for item in gaps if item != "red_flags"]
        return gaps[:3]
