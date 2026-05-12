from __future__ import annotations

from ..schemas import DialogueContext, MemorySnapshot


class ContextRouter:
    def route(self, context: DialogueContext, snapshot: MemorySnapshot) -> dict[str, object]:
        intent = (context.intent or "").lower()
        use_physiology = bool(snapshot.symptom.baseline_signals or snapshot.symptom.trend_signals)
        use_continuity = bool(snapshot.conversational.continuity_reference or snapshot.narrative.prior_discussions)
        use_reassurance = context.risk_level.lower() not in {"high", "critical", "emergency"}
        if intent in {"risk_explanation", "report_analysis"}:
            use_physiology = True
        if intent in {"greeting", "gratitude", "acknowledgement"}:
            use_physiology = False
        if context.mode == "expert":
            use_continuity = True
            use_physiology = True
        return {
            "use_physiology": use_physiology,
            "use_continuity": use_continuity,
            "use_reassurance": use_reassurance,
            "followup_limit": 0 if context.intent in {"gratitude", "farewell"} else 1 if context.mode == "casual" else 2,
        }
