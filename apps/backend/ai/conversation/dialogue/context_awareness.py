from __future__ import annotations

from ..schemas import DialogueContext, MemorySnapshot


class ContextAwareness:
    def build(self, context: DialogueContext, snapshot: MemorySnapshot) -> dict[str, list[str] | str]:
        physiological = []
        physiological.extend(snapshot.symptom.baseline_signals[:2])
        physiological.extend(snapshot.symptom.trend_signals[:2])
        if not physiological and snapshot.symptom.anomaly_progression:
            physiological.extend(snapshot.symptom.anomaly_progression[:2])

        grounding_line = ""
        if physiological:
            grounding_line = physiological[0]
        elif snapshot.narrative.longitudinal_summary:
            grounding_line = snapshot.narrative.longitudinal_summary
        elif context.response_payload.get("risk_summary"):
            grounding_line = str(context.response_payload.get("risk_summary")).strip()

        return {
            "physiological_signals": physiological[:4],
            "anomaly_signals": snapshot.symptom.anomaly_progression[:3],
            "recovery_signals": snapshot.symptom.recovery_trajectory[:2],
            "grounding_line": grounding_line,
        }
