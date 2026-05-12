from __future__ import annotations

from ..schemas import NarrativeContext, ReasoningCard


class RespiratoryReasoner:
    def analyze(self, context: NarrativeContext) -> list[ReasoningCard]:
        spo2 = context.metric("spo2")
        resp = context.metric("respiratory_rate")
        aqi = context.metric("air_quality")
        if spo2 is None and resp is None:
            return []
        concern = bool(
            (spo2 and spo2.current is not None and spo2.current < 95)
            or (resp and resp.current is not None and resp.current > 20)
        )
        if not concern:
            return []
        evidence = []
        if spo2 is not None:
            evidence.append(f"SpO2 is {spo2.formatted_current()} relative to {spo2.formatted_baseline()}.")
        if resp is not None:
            evidence.append(f"Respiratory rate is {resp.formatted_current()}.")
        if aqi is not None and aqi.current is not None:
            evidence.append(f"Air quality is {aqi.formatted_current()}.")
        return [
            ReasoningCard(
                kind="physiology",
                domain="respiratory",
                title="Respiratory signals deserve closer observation",
                summary="Oxygen or breathing-rate trends look less comfortable than usual, which matters more if symptoms such as breathlessness, cough, or fatigue are present.",
                severity="high" if spo2 and (spo2.current or 100) <= 93 else "medium",
                confidence=0.77,
                timeframe="24h",
                evidence=evidence,
                metrics=["spo2", "respiratory_rate", "air_quality"],
                recommendations=["Track whether this is persistent and seek in-person care promptly if breathing symptoms are new, severe, or worsening."],
                tags=["respiratory"],
            )
        ]
