from __future__ import annotations

from ..schemas import NarrativeContext, ReasoningCard


class FatigueReasoner:
    def analyze(self, context: NarrativeContext) -> list[ReasoningCard]:
        sleep = context.metric("sleep_duration")
        recovery = context.metric("recovery_score")
        rhr = context.metric("resting_hr")
        activity = context.metric("activity_steps")
        conditions = [
            bool(sleep and sleep.status == "reduced"),
            bool(recovery and recovery.status == "reduced"),
            bool(rhr and rhr.status == "elevated"),
            bool(activity and activity.status == "reduced"),
        ]
        if sum(conditions) < 2:
            return []
        evidence = []
        for signal in (sleep, recovery, rhr, activity):
            if signal is not None:
                evidence.append(f"{signal.label} is {signal.formatted_current()} versus {signal.formatted_baseline()}.")
        return [
            ReasoningCard(
                kind="cluster",
                domain="fatigue",
                title="Multi-signal fatigue pattern is forming",
                summary="Lower sleep, reduced recovery, elevated resting heart rate, and softer activity together fit a combined fatigue interpretation better than any one metric alone.",
                severity="high" if sum(conditions) >= 3 else "medium",
                confidence=0.86,
                timeframe="7d",
                evidence=evidence,
                metrics=["sleep_duration", "recovery_score", "resting_hr", "activity_steps"],
                recommendations=["Reduce recovery debt first, then judge whether activity and heart-rate patterns normalize together."],
                tags=["fatigue_cluster", "cross_metric"],
            )
        ]
