from __future__ import annotations

from ..utils import acceleration, category_history, category_score, clamp, metric_value, trend_direction
from .common import build_signal


class StressMonitor:
    DOMAIN = "stress"

    @staticmethod
    def evaluate(context: dict) -> dict:
        stress_score = category_score(context, "stress")
        stress_level = metric_value(context, "stress")
        avg_rhr = metric_value(context, "avg_rhr", "resting_hr")
        history = category_history(context, "stress")

        if stress_score is not None:
            risk = 100.0 - float(stress_score)
        else:
            normalized_level = (max(1.0, min(10.0, float(stress_level or 4.0))) - 1.0) / 9.0
            risk = normalized_level * 100.0
        if avg_rhr is not None and avg_rhr > 64.0:
            risk += (avg_rhr - 64.0) * 1.3

        risk = clamp(risk)
        change = acceleration(history or [100.0 - risk])
        direction = trend_direction((history[-1] - history[0]) if len(history) > 1 else risk * 0.01, lower_is_worse=True)
        summary = (
            "Physiologic stress appears to be accumulating rather than clearing between recovery windows."
            if risk >= 55.0
            else "Stress burden looks manageable, but continued load may still compound if recovery slips."
        )
        signal = build_signal(
            domain=StressMonitor.DOMAIN,
            kind="accumulation",
            summary=summary,
            risk_score=risk,
            confidence=0.78 if stress_score is not None else 0.68,
            direction=direction,
            value=stress_score if stress_score is not None else stress_level,
            baseline_delta=(history[-1] - history[0]) if len(history) > 1 else None,
            persistence_days=float(len(history[-3:])) if history else 0.0,
            acceleration=abs(change),
            monitor="stress_monitor",
            supporting_metrics={
                "stress_score": stress_score,
                "stress_level": stress_level,
                "avg_rhr": avg_rhr,
            },
            recommended_actions=[
                "Break up cumulative strain with lighter recovery blocks.",
                "Use sleep protection and lower-intensity pacing if the pattern persists.",
            ],
            tags=["stress_accumulation", "autonomic_load"],
        )
        return signal.model_dump(mode="json")
