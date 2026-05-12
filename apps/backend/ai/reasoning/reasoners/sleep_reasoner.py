from __future__ import annotations

from ..schemas import NarrativeContext, ReasoningCard


class SleepReasoner:
    def analyze(self, context: NarrativeContext) -> list[ReasoningCard]:
        sleep = context.metric("sleep_duration")
        rhr = context.metric("resting_hr")
        if sleep is None or sleep.current is None:
            return []
        if sleep.status not in {"reduced", "elevated"} and (sleep.current or 0) >= 6.5:
            return []
        evidence = [f"Sleep duration is {sleep.formatted_current()} versus a baseline near {sleep.formatted_baseline()}."]
        if rhr is not None:
            evidence.append(f"Resting heart rate is {rhr.formatted_current()} versus {rhr.formatted_baseline()}.")
        return [
            ReasoningCard(
                kind="physiology",
                domain="sleep",
                title="Sleep consistency is likely contributing to reduced resilience",
                summary="Sleep has been running below your usual pattern, and that can amplify overnight heart-rate strain and next-day recovery drag.",
                severity="medium",
                confidence=0.8,
                timeframe="7d",
                evidence=evidence,
                metrics=["sleep_duration", "resting_hr"],
                recommendations=["Protect the next few sleep windows and watch whether recovery normalizes as sleep regularity improves."],
                tags=["sleep"],
            )
        ]
