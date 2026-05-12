from __future__ import annotations

from ..schemas import NarrativeContext, ReasoningCard


class BehavioralReasoner:
    def analyze(self, context: NarrativeContext) -> list[ReasoningCard]:
        steps = context.metric("activity_steps")
        sleep = context.metric("sleep_duration")
        if steps is None:
            return []
        if steps.status not in {"reduced", "elevated"} and not context.memory.get("recommendation_carryover"):
            return []
        evidence = [f"Activity is {steps.formatted_current()} compared with {steps.formatted_baseline()}."]
        if sleep is not None:
            evidence.append(f"Sleep is {sleep.formatted_current()} compared with {sleep.formatted_baseline()}.")
        return [
            ReasoningCard(
                kind="behavior",
                domain="behavioral",
                title="Behavioral drift may be reinforcing the physiology",
                summary="The recent pattern suggests your routine has moved away from the habits that usually support steadier recovery and metabolic balance.",
                severity="medium",
                confidence=0.68,
                timeframe="30d",
                evidence=evidence + [str(item) for item in (context.memory.get("recommendation_carryover") or [])[:2]],
                metrics=["activity_steps", "sleep_duration"],
                recommendations=["Pick one habit to stabilize first, such as daily movement floor or sleep timing, so the trend can reverse sustainably."],
                tags=["behavioral_drift"],
            )
        ]
