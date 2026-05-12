from __future__ import annotations

from ..core.temporal_projection_engine import TemporalProjectionEngine, _safe_float
from ..schemas.prediction_metadata import ProjectionContributor


class RespiratoryForecaster:
    DOMAIN = "respiratory"

    @staticmethod
    def forecast(context: dict, window: str) -> dict:
        current_signals = context.get("wearable_signals", {}).get("current", {})
        latest_health = context.get("latest_health_payload", {})
        category = (latest_health.get("category_scores") or {}).get("respiratory_score", {})
        score_history = [100.0 - float(value) for value in context.get("category_histories", {}).get("respiratory_score", [])]
        current_risk = 100.0 - _safe_float(category.get("score"), 78.0)
        baseline = 100.0 - _safe_float(context.get("baseline_profile").reference_value("respiratory_score", 78.0), 78.0)
        contributors = [
            ProjectionContributor(
                label="SpO2",
                value=current_signals.get("spo2"),
                direction="lower",
                impact=0.42,
                detail="Lower oxygen saturation materially affects respiratory projections.",
            ),
            ProjectionContributor(
                label="sleep recovery",
                value=current_signals.get("sleep_hours"),
                direction="lower",
                impact=0.16,
                detail="Poor recovery can amplify respiratory instability.",
            ),
        ]
        explanation = "Respiratory outlook remains sensitive to oxygen saturation stability and recovery quality over the next few windows."
        recommendation = "Watch for new respiratory symptoms and escalate clinician review if projected strain rises alongside symptom change."
        return TemporalProjectionEngine.project(
            domain=RespiratoryForecaster.DOMAIN,
            window=window,
            current_value=current_risk,
            history=score_history or [100.0 - float(value) for value in context.get("wearable_signals", {}).get("histories", {}).get("spo2", []) if value is not None],
            baseline_value=baseline,
            higher_is_better=False,
            contributors=contributors,
            explanation_hint=explanation,
            recommendation=recommendation,
            source_count=2,
        ).model_dump()
