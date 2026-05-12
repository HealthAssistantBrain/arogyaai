from __future__ import annotations

from ..core.temporal_projection_engine import TemporalProjectionEngine, _safe_float
from ..schemas.prediction_metadata import ProjectionContributor


class MetabolicForecaster:
    DOMAIN = "metabolic"

    @staticmethod
    def forecast(context: dict, window: str) -> dict:
        latest_health = context.get("latest_health_payload", {})
        lab_current = context.get("lab_signals", {}).get("current", {})
        category = (latest_health.get("category_scores") or {}).get("metabolic_score", {})
        score_history = [100.0 - float(value) for value in context.get("category_histories", {}).get("metabolic_score", [])]
        current_risk = 100.0 - _safe_float(category.get("score"), 72.0)
        baseline = 100.0 - _safe_float(context.get("baseline_profile").reference_value("metabolic_score", 72.0), 72.0)
        contributors = [
            ProjectionContributor(
                label="glucose progression",
                value=lab_current.get("glucose"),
                direction="higher",
                impact=0.36,
                detail="Glucose progression influences projected metabolic instability.",
            ),
            ProjectionContributor(
                label="cholesterol trend",
                value=lab_current.get("cholesterol"),
                direction="higher",
                impact=0.22,
                detail="Lipid burden contributes to longer-horizon risk drift.",
            ),
            ProjectionContributor(
                label="body mass / lifestyle",
                value=context.get("feature_snapshot", {}).get("bmi"),
                direction="higher",
                impact=0.18,
                detail="Lifestyle pressure affects metabolic resilience over time.",
            ),
        ]
        explanation = "Lab progression and lifestyle load suggest metabolic instability could build if recovery and nutrition patterns do not improve."
        recommendation = "Track glucose and sleep consistency closely and escalate routine follow-up if this projected instability persists."
        return TemporalProjectionEngine.project(
            domain=MetabolicForecaster.DOMAIN,
            window=window,
            current_value=current_risk,
            history=score_history or [float(value) for value in context.get("lab_signals", {}).get("histories", {}).get("glucose", [])],
            baseline_value=baseline,
            higher_is_better=False,
            contributors=contributors,
            explanation_hint=explanation,
            recommendation=recommendation,
            source_count=3,
        ).model_dump()
