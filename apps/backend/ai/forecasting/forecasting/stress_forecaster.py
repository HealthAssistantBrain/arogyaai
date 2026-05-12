from __future__ import annotations

from ..core.temporal_projection_engine import TemporalProjectionEngine, _safe_float
from ..schemas.prediction_metadata import ProjectionContributor


class StressForecaster:
    DOMAIN = "stress"

    @staticmethod
    def forecast(context: dict, window: str) -> dict:
        current_signals = context.get("wearable_signals", {}).get("current", {})
        latest_health = context.get("latest_health_payload", {})
        category = (latest_health.get("category_scores") or {}).get("stress_score", {})
        score_history = [100.0 - float(value) for value in context.get("category_histories", {}).get("stress_score", [])]
        current_risk = 100.0 - _safe_float(category.get("score"), 71.0)
        baseline = 100.0 - _safe_float(context.get("baseline_profile").reference_value("stress_score", 71.0), 71.0)
        contributors = [
            ProjectionContributor(
                label="resting heart rate",
                value=current_signals.get("resting_hr"),
                direction="higher",
                impact=0.28,
                detail="Sustained RHR elevation often tracks physiologic stress burden.",
            ),
            ProjectionContributor(
                label="HRV resilience",
                value=current_signals.get("hrv"),
                direction="lower",
                impact=0.3,
                detail="Reduced HRV can signal lower recovery reserve.",
            ),
            ProjectionContributor(
                label="fatigue proxy",
                value=current_signals.get("fatigue_proxy"),
                direction="higher",
                impact=0.2,
                detail="Cumulative fatigue can amplify stress accumulation.",
            ),
        ]
        explanation = "Stress burden may accumulate if elevated resting load and reduced resilience continue across the next few windows."
        recommendation = "Favor recovery-supportive routines and reduce stacked stressors while this projected load remains elevated."
        return TemporalProjectionEngine.project(
            domain=StressForecaster.DOMAIN,
            window=window,
            current_value=current_risk,
            history=score_history or [float(value) for value in context.get("wearable_signals", {}).get("histories", {}).get("fatigue_proxy", [])],
            baseline_value=baseline,
            higher_is_better=False,
            contributors=contributors,
            explanation_hint=explanation,
            recommendation=recommendation,
            source_count=3,
        ).model_dump()
