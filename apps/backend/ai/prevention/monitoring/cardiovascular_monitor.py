from __future__ import annotations

from ..utils import acceleration, category_history, category_score, clamp, metric_value, trend_direction
from .common import build_signal


class CardiovascularMonitor:
    DOMAIN = "cardiovascular"

    @staticmethod
    def evaluate(context: dict) -> dict:
        cardio_score = category_score(context, "cardiovascular")
        avg_rhr = metric_value(context, "avg_rhr", "resting_hr")
        systolic_bp = metric_value(context, "systolic_bp", "blood_pressure_systolic")
        diastolic_bp = metric_value(context, "diastolic_bp", "blood_pressure_diastolic")
        history = category_history(context, "cardiovascular")

        risk = 100.0 - float(cardio_score if cardio_score is not None else 76.0)
        if avg_rhr is not None and avg_rhr > 62.0:
            risk += (avg_rhr - 62.0) * 1.8
        if systolic_bp is not None and systolic_bp >= 125.0:
            risk += (systolic_bp - 125.0) * 1.15
        if diastolic_bp is not None and diastolic_bp >= 80.0:
            risk += (diastolic_bp - 80.0) * 1.6

        risk = clamp(risk)
        change = acceleration(history or [100.0 - risk])
        direction = trend_direction((history[-1] - history[0]) if len(history) > 1 else risk * 0.01, lower_is_worse=True)
        summary = (
            "Cardiovascular load is drifting upward and deserves closer observation."
            if risk >= 55.0
            else "Cardiovascular stability is reasonably preserved, but the trend still warrants tracking."
        )
        signal = build_signal(
            domain=CardiovascularMonitor.DOMAIN,
            kind="drift",
            summary=summary,
            risk_score=risk,
            confidence=0.84 if cardio_score is not None else 0.7,
            direction=direction,
            value=cardio_score if cardio_score is not None else avg_rhr,
            baseline_delta=(history[-1] - history[0]) if len(history) > 1 else None,
            persistence_days=float(len(history[-3:])) if history else 0.0,
            acceleration=abs(change),
            monitor="cardiovascular_monitor",
            supporting_metrics={
                "cardiovascular_score": cardio_score,
                "avg_rhr": avg_rhr,
                "systolic_bp": systolic_bp,
                "diastolic_bp": diastolic_bp,
            },
            recommended_actions=[
                "Favor lighter exertion while recovery and resting pulse settle.",
                "Recheck cardiovascular readings if the drift remains elevated.",
            ],
            tags=["cardiovascular_drift", "resting_load"],
        )
        return signal.model_dump(mode="json")
