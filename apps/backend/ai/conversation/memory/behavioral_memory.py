from __future__ import annotations

from ..schemas import BehavioralMemorySnapshot, DialogueContext


class BehavioralMemoryBuilder:
    def build(self, context: DialogueContext) -> BehavioralMemorySnapshot:
        user_context = context.user_context if isinstance(context.user_context, dict) else {}
        tone_adaptation = user_context.get("tone_adaptation") if isinstance(user_context.get("tone_adaptation"), dict) else {}
        emotional = context.emotional_context if isinstance(context.emotional_context, dict) else {}
        memory_emotional = user_context.get("memory_emotional_context") if isinstance(user_context.get("memory_emotional_context"), dict) else {}
        semantic = user_context.get("memory_summary") if isinstance(user_context.get("memory_summary"), dict) else {}
        communication_preferences = user_context.get("communication_preferences") if isinstance(
            user_context.get("communication_preferences"),
            dict,
        ) else {}

        distress = str(emotional.get("dominant_emotion") or memory_emotional.get("tone") or "neutral").lower()
        explanation_preference = str(
            communication_preferences.get("preferred_explanation_depth")
            or semantic.get("preferred_explanation_depth")
            or ("detailed" if context.mode == "expert" else "balanced")
        ).lower()
        pacing_preference = str(tone_adaptation.get("response_length") or "steady").lower()
        reassurance_preference = "measured" if context.risk_level.lower() in {"high", "critical", "emergency"} else "steady"
        communication_style = str(tone_adaptation.get("tone_modifier") or emotional.get("adaptation", {}).get("tone") or "calm").lower()

        return BehavioralMemorySnapshot(
            explanation_preference="concise" if explanation_preference in {"short", "brief", "micro"} else explanation_preference,
            communication_style=communication_style,
            pacing_preference=pacing_preference,
            question_tolerance="focused" if context.mode in {"casual", "medical"} else "exploratory",
            reassurance_preference=reassurance_preference,
            user_state=distress,
        )
