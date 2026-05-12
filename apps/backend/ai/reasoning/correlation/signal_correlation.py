from __future__ import annotations

from ..schemas import NarrativeContext, ReasoningCard


class SignalCorrelation:
    def analyze(self, context: NarrativeContext) -> list[ReasoningCard]:
        cards: list[ReasoningCard] = []
        sleep = context.metric("sleep_duration")
        rhr = context.metric("resting_hr")
        hrv = context.metric("hrv")
        glucose = context.metric("glucose")
        activity = context.metric("activity_steps")
        spo2 = context.metric("spo2")
        resp = context.metric("respiratory_rate")
        recovery = context.metric("recovery_score")
        stress = context.metric("stress_score")

        if sleep and rhr and sleep.status == "reduced" and rhr.status == "elevated":
            cards.append(
                ReasoningCard(
                    kind="correlation",
                    domain="sleep_cardiovascular",
                    title="Short sleep is lining up with higher overnight strain",
                    summary="Sleep has fallen below your usual pattern while resting heart rate is higher than baseline, a combination that often tracks with poorer recovery quality.",
                    severity="high",
                    confidence=0.84,
                    timeframe="7d",
                    evidence=[
                        f"Sleep {sleep.formatted_current()} vs {sleep.formatted_baseline()} baseline.",
                        f"Resting heart rate {rhr.formatted_current()} vs {rhr.formatted_baseline()} baseline.",
                    ],
                    metrics=["sleep_duration", "resting_hr"],
                    tags=["causal_correlation"],
                )
            )
        if recovery and stress and recovery.status == "reduced" and stress.status == "elevated":
            cards.append(
                ReasoningCard(
                    kind="correlation",
                    domain="stress_recovery",
                    title="Higher stress is likely weighing on recovery",
                    summary="Stress and recovery are moving in opposite directions, which fits a strain-recovery mismatch rather than isolated noise.",
                    severity="medium",
                    confidence=0.79,
                    timeframe="7d",
                    evidence=[
                        f"Stress {stress.formatted_current()} vs {stress.formatted_baseline()}.",
                        f"Recovery {recovery.formatted_current()} vs {recovery.formatted_baseline()}.",
                    ],
                    metrics=["stress_score", "recovery_score"],
                    tags=["causal_correlation"],
                )
            )
        if glucose and activity and glucose.status == "elevated" and activity.status == "reduced":
            cards.append(
                ReasoningCard(
                    kind="correlation",
                    domain="glucose_activity",
                    title="Lower activity may be contributing to softer glucose control",
                    summary="Glucose is running above baseline while movement is below your usual pattern, which is a clinically plausible interaction for short-term metabolic instability.",
                    severity="medium",
                    confidence=0.77,
                    timeframe="30d",
                    evidence=[
                        f"Glucose {glucose.formatted_current()} vs {glucose.formatted_baseline()}.",
                        f"Activity {activity.formatted_current()} vs {activity.formatted_baseline()}.",
                    ],
                    metrics=["glucose", "activity_steps"],
                    tags=["causal_correlation"],
                )
            )
        if spo2 and resp and spo2.current is not None and spo2.current < 95 and resp.current is not None and resp.current > 20:
            cards.append(
                ReasoningCard(
                    kind="correlation",
                    domain="respiratory_load",
                    title="Oxygen and breathing-rate signals both suggest respiratory strain",
                    summary="Lower SpO2 with a faster breathing rate deserves more caution than either change alone, especially if symptoms are also present.",
                    severity="high",
                    confidence=0.82,
                    timeframe="24h",
                    evidence=[
                        f"SpO2 {spo2.formatted_current()}",
                        f"Respiratory rate {resp.formatted_current()}",
                    ],
                    metrics=["spo2", "respiratory_rate"],
                    tags=["causal_correlation"],
                )
            )
        return cards
