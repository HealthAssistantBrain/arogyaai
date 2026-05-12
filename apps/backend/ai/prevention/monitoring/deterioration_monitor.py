from __future__ import annotations

from ..utils import (
    acceleration,
    clamp,
    current_overall_risk,
    delta,
    safe_list,
    top_forecast_risk,
    trend_direction,
)
from .common import build_signal


class DeteriorationMonitor:
    DOMAIN = "deterioration"

    @staticmethod
    def evaluate(context: dict) -> dict:
        risk_history = [float(item) for item in safe_list(context.get("risk_history")) if item is not None]
        current_risk = current_overall_risk(context)
        projected_risk = top_forecast_risk(context, window="72h")
        history_delta = delta(risk_history)
        risk = clamp(max(current_risk, projected_risk * 0.85) + max(0.0, history_delta) * 0.35)
        signal = build_signal(
            domain=DeteriorationMonitor.DOMAIN,
            kind="progression",
            summary=(
                "The recent pattern suggests health strain is progressing rather than stabilizing."
                if risk >= 55.0
                else "Overall deterioration risk is limited right now, but continued monitoring is still sensible."
            ),
            risk_score=risk,
            confidence=0.86 if risk_history else 0.68,
            direction=trend_direction(history_delta, lower_is_worse=False),
            value=current_risk,
            baseline_delta=history_delta if risk_history else None,
            persistence_days=float(min(7, len(risk_history))),
            acceleration=abs(acceleration(risk_history or [current_risk, projected_risk])),
            monitor="deterioration_monitor",
            supporting_metrics={
                "current_overall_risk": current_risk,
                "projected_risk_72h": projected_risk,
                "risk_history_points": len(risk_history),
            },
            recommended_actions=[
                "Increase observation frequency until the trend stops accelerating.",
                "Prioritize the top recovery and strain-reduction actions rather than diffuse changes.",
            ],
            tags=["deterioration_progression", "forecast_linked"],
        )
        return signal.model_dump(mode="json")
