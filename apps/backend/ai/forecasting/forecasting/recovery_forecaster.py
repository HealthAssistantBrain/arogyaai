from __future__ import annotations

from ..core.temporal_projection_engine import TemporalProjectionEngine, _safe_float
from ..schemas.prediction_metadata import ProjectionContributor


class RecoveryForecaster:
    DOMAIN = "recovery"

    @staticmethod
    def forecast(context: dict, window: str) -> dict:
        current_signals = context.get("wearable_signals", {}).get("current", {})
        latest_health = context.get("latest_health_payload", {})
        recovery_signals = (latest_health.get("metadata") or {}).get("recovery_signals", {})
        category = (latest_health.get("category_scores") or {}).get("recovery_score", {})
        score_history = [100.0 - float(value) for value in context.get("category_histories", {}).get("recovery_score", [])]
        current_risk = 100.0 - _safe_float(category.get("score"), 74.0)
        baseline = 100.0 - _safe_float(context.get("baseline_profile").reference_value("recovery_score", 74.0), 74.0)
        contributors = [
            ProjectionContributor(
                label="recovery proxy",
                value=recovery_signals.get("recovery_proxy"),
                direction="lower",
                impact=0.34,
                detail="Weakening recovery proxy often precedes fatigue accumulation.",
            ),
            ProjectionContributor(
                label="sleep duration",
                value=current_signals.get("sleep_hours"),
                direction="lower",
                impact=0.24,
                detail="Sleep debt reduces projected recovery capacity.",
            ),
            ProjectionContributor(
                label="resting heart rate",
                value=current_signals.get("resting_hr"),
                direction="higher",
                impact=0.2,
                detail="Elevated resting HR can indicate incomplete recovery.",
            ),
        ]
        explanation = "Recovery consistency appears soft enough that resilience may slip if recent sleep and autonomic patterns continue."
        recommendation = "Use lighter load, extra sleep opportunity, and symptom-aware pacing while this recovery projection stays elevated."
        return TemporalProjectionEngine.project(
            domain=RecoveryForecaster.DOMAIN,
            window=window,
            current_value=current_risk,
            history=score_history,
            baseline_value=baseline,
            higher_is_better=False,
            contributors=contributors,
            explanation_hint=explanation,
            recommendation=recommendation,
            source_count=3,
        ).model_dump()
