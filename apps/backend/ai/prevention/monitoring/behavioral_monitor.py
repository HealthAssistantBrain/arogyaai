from __future__ import annotations

from ..utils import clamp, metric_value
from .common import build_signal


class BehavioralMonitor:
    DOMAIN = "behavior"

    @staticmethod
    def evaluate(context: dict) -> dict:
        steps_avg = metric_value(context, "steps_avg_7d", "activity_level")
        sleep_efficiency = metric_value(context, "sleep_efficiency", "sleep_score")
        lifestyle_score = metric_value(context, "lifestyle_score")
        activity_score = metric_value(context, "activity_score")

        risk = 0.0
        if steps_avg is not None and steps_avg < 6500.0:
            risk += (6500.0 - steps_avg) / 85.0
        if sleep_efficiency is not None and sleep_efficiency < 78.0:
            risk += (78.0 - sleep_efficiency) * 0.55
        if lifestyle_score is not None:
            risk += max(0.0, 75.0 - lifestyle_score) * 0.45
        if activity_score is not None:
            risk += max(0.0, 72.0 - activity_score) * 0.35

        risk = clamp(risk)
        summary = (
            "Behavioral consistency is drifting enough to make recovery and resilience less reliable."
            if risk >= 55.0
            else "Daily habits are mostly stable, but tighter consistency would strengthen prevention."
        )
        signal = build_signal(
            domain=BehavioralMonitor.DOMAIN,
            kind="drift",
            summary=summary,
            risk_score=risk,
            confidence=0.72,
            direction="worsening" if risk >= 45.0 else "stable",
            value=lifestyle_score if lifestyle_score is not None else activity_score,
            baseline_delta=None,
            persistence_days=2.0 if risk >= 45.0 else 0.0,
            acceleration=0.0,
            monitor="behavioral_monitor",
            supporting_metrics={
                "steps_avg_7d": steps_avg,
                "sleep_efficiency": sleep_efficiency,
                "lifestyle_score": lifestyle_score,
                "activity_score": activity_score,
            },
            recommended_actions=[
                "Tighten sleep timing and keep activity more consistent across the week.",
                "Use smaller, repeatable recovery habits instead of waiting for a reset day.",
            ],
            tags=["behavioral_drift", "adherence_risk"],
        )
        return signal.model_dump(mode="json")
