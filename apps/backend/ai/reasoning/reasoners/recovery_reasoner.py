from __future__ import annotations

from ..schemas import NarrativeContext, ReasoningCard


class RecoveryReasoner:
    def analyze(self, context: NarrativeContext) -> list[ReasoningCard]:
        recovery = context.metric("recovery_score")
        stress = context.metric("stress_score")
        sleep = context.metric("sleep_duration")
        if recovery is None and stress is None:
            return []
        if recovery and recovery.status not in {"elevated", "reduced"} and not (stress and stress.status == "elevated"):
            return []
        evidence = []
        if recovery is not None:
            evidence.append(f"Recovery is {recovery.formatted_current()} relative to {recovery.formatted_baseline()} recently.")
        if stress is not None:
            evidence.append(f"Stress is {stress.formatted_current()} relative to {stress.formatted_baseline()} recently.")
        if sleep is not None:
            evidence.append(f"Sleep duration is {sleep.formatted_current()} relative to {sleep.formatted_baseline()}.")
        return [
            ReasoningCard(
                kind="physiology",
                domain="recovery",
                title="Recovery reserve looks compressed",
                summary="Recovery appears lower than usual, especially when the current pattern is paired with shorter sleep or higher stress load.",
                severity="medium",
                confidence=0.76,
                timeframe="7d",
                evidence=evidence,
                metrics=["recovery_score", "stress_score", "sleep_duration"],
                recommendations=["Bias the next day or two toward lighter load, more sleep consistency, and lower evening stimulation."],
                tags=["recovery"],
            )
        ]
