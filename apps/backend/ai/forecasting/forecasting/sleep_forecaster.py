from __future__ import annotations

from ..core.temporal_projection_engine import TemporalProjectionEngine, _safe_float
from ..schemas.prediction_metadata import ProjectionContributor


class SleepForecaster:
    DOMAIN = "sleep"

    @staticmethod
    def forecast(context: dict, window: str) -> dict:
        current_signals = context.get("wearable_signals", {}).get("current", {})
        latest_health = context.get("latest_health_payload", {})
        category = (latest_health.get("category_scores") or {}).get("sleep_score", {})
        score_history = [100.0 - float(value) for value in context.get("category_histories", {}).get("sleep_score", [])]
        current_risk = 100.0 - _safe_float(category.get("score"), 70.0)
        baseline = 100.0 - _safe_float(context.get("baseline_profile").reference_value("sleep_score", 70.0), 70.0)
        contributors = [
            ProjectionContributor(
                label="sleep duration",
                value=current_signals.get("sleep_hours"),
                direction="lower",
                impact=0.34,
                detail="Recent sleep duration directly shapes projected sleep debt.",
            ),
            ProjectionContributor(
                label="sleep efficiency",
                value=current_signals.get("sleep_efficiency"),
                direction="lower",
                impact=0.28,
                detail="Lower efficiency suggests fragmented recovery.",
            ),
            ProjectionContributor(
                label="fatigue proxy",
                value=current_signals.get("fatigue_proxy"),
                direction="higher",
                impact=0.18,
                detail="Rising fatigue proxy often compounds sleep deterioration.",
            ),
        ]
        explanation = "Recent sleep duration and efficiency trends suggest sleep debt may accumulate if the current pattern holds."
        recommendation = "Prioritize a more consistent sleep window before this projected debt compounds into daytime fatigue."
        return TemporalProjectionEngine.project(
            domain=SleepForecaster.DOMAIN,
            window=window,
            current_value=current_risk,
            history=score_history or [float(value) for value in context.get("wearable_signals", {}).get("histories", {}).get("sleep", [])],
            baseline_value=baseline,
            higher_is_better=False,
            contributors=contributors,
            explanation_hint=explanation,
            recommendation=recommendation,
            source_count=3,
        ).model_dump()
