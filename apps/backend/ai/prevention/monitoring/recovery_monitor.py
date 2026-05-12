from __future__ import annotations

from ..utils import (
    acceleration,
    category_history,
    category_score,
    clamp,
    consecutive_breach_count,
    metric_value,
    trend_direction,
)
from .common import build_signal


class RecoveryMonitor:
    DOMAIN = "recovery"

    @staticmethod
    def evaluate(context: dict) -> dict:
        recovery_score = category_score(context, "recovery")
        recovery_proxy = metric_value(context, "recovery_proxy")
        sleep_efficiency = metric_value(context, "sleep_efficiency", "sleep_score")
        sleep_duration = metric_value(context, "sleep_duration", "sleep")
        history = category_history(context, "recovery")
        score_basis = recovery_score if recovery_score is not None else recovery_proxy if recovery_proxy is not None else 72.0

        risk = 100.0 - float(score_basis)
        if sleep_efficiency is not None and sleep_efficiency < 78.0:
            risk += (78.0 - sleep_efficiency) * 0.45
        if sleep_duration is not None and sleep_duration < 7.0:
            risk += (7.0 - sleep_duration) * 8.0

        change = acceleration(history or [score_basis])
        persistence = consecutive_breach_count(history or [score_basis], threshold=65.0, lower_is_worse=True)
        direction = trend_direction((history[-1] - history[0]) if len(history) > 1 else -risk * 0.01, lower_is_worse=True)
        summary = (
            "Recovery markers have softened and may be less stable than your recent pattern."
            if risk >= 55.0
            else "Recovery is broadly stable, but it still benefits from sleep consistency."
        )
        signal = build_signal(
            domain=RecoveryMonitor.DOMAIN,
            kind="instability",
            summary=summary,
            risk_score=clamp(risk),
            confidence=0.82 if history else 0.7,
            direction=direction,
            value=recovery_score if recovery_score is not None else recovery_proxy,
            baseline_delta=(history[-1] - history[0]) if len(history) > 1 else None,
            persistence_days=float(persistence),
            acceleration=abs(change),
            monitor="recovery_monitor",
            supporting_metrics={
                "recovery_score": recovery_score,
                "recovery_proxy": recovery_proxy,
                "sleep_efficiency": sleep_efficiency,
                "sleep_duration": sleep_duration,
            },
            recommended_actions=[
                "Protect a full sleep opportunity for the next several nights.",
                "Reduce stacked high-strain activity until recovery stabilizes.",
            ],
            tags=["recovery_instability", "sleep_recovery_link"],
        )
        return signal.model_dump(mode="json")
