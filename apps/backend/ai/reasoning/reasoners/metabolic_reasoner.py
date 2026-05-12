from __future__ import annotations

from ..schemas import NarrativeContext, ReasoningCard


class MetabolicReasoner:
    def analyze(self, context: NarrativeContext) -> list[ReasoningCard]:
        glucose = context.metric("glucose")
        hba1c = context.metric("hba1c")
        activity = context.metric("activity_steps")
        if glucose is None and hba1c is None:
            return []
        if glucose and glucose.status not in {"elevated", "reduced"} and not (hba1c and (hba1c.current or 0) >= 5.7):
            return []
        evidence = []
        if glucose is not None:
            evidence.append(f"Glucose is {glucose.formatted_current()} compared with a recent baseline near {glucose.formatted_baseline()}.")
        if hba1c is not None and hba1c.current is not None:
            evidence.append(f"HbA1c is {hba1c.formatted_current()}.")
        if activity is not None:
            evidence.append(f"Activity is {activity.formatted_current()} versus a usual pattern near {activity.formatted_baseline()}.")
        return [
            ReasoningCard(
                kind="physiology",
                domain="metabolic",
                title="Metabolic resilience may be softer right now",
                summary="Glucose-related signals look less favorable when paired with reduced activity, which can make short-term metabolic control less stable.",
                severity="medium",
                confidence=0.72,
                timeframe="30d",
                evidence=evidence,
                metrics=["glucose", "hba1c", "activity_steps"],
                recommendations=["Focus on meal-to-movement consistency and watch whether the pattern holds across repeated readings."],
                tags=["metabolic"],
            )
        ]
