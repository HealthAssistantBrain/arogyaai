from __future__ import annotations

from ..schemas import NarrativeContext, ReasoningCard


class CardiovascularReasoner:
    def analyze(self, context: NarrativeContext) -> list[ReasoningCard]:
        rhr = context.metric("resting_hr")
        sbp = context.metric("systolic_bp")
        hrv = context.metric("hrv")
        if rhr is None and sbp is None:
            return []
        if not any(signal and signal.status in {"elevated", "reduced"} for signal in (rhr, sbp, hrv)):
            return []
        evidence = []
        metrics = []
        if rhr is not None:
            evidence.append(f"Resting heart rate is {rhr.formatted_current()} versus a recent baseline near {rhr.formatted_baseline()}.")
            metrics.append("resting_hr")
        if sbp is not None:
            evidence.append(f"Systolic blood pressure is {sbp.formatted_current()}.")
            metrics.append("systolic_bp")
        if hrv is not None and hrv.baseline is not None and hrv.current is not None:
            evidence.append(f"HRV is {hrv.formatted_current()} versus a baseline near {hrv.formatted_baseline()}.")
            metrics.append("hrv")
        return [
            ReasoningCard(
                kind="physiology",
                domain="cardiovascular",
                title="Cardiovascular strain markers are elevated",
                summary="Heart-rate and pressure signals suggest higher cardiovascular load than your recent baseline, especially if this pattern persists across several days.",
                severity="high" if sbp and (sbp.current or 0) >= 140 else "medium",
                confidence=0.78,
                timeframe="7d",
                evidence=evidence,
                metrics=metrics,
                recommendations=[
                    "Recheck resting values under similar conditions and look for persistence rather than reacting to a single reading.",
                ],
                tags=["cardiovascular", "baseline_aware"],
            )
        ]
