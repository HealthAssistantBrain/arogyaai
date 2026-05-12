from __future__ import annotations

from ..core.temporal_projection_engine import TemporalProjectionEngine, _safe_float
from ..schemas.prediction_metadata import ProjectionContributor


class CardiovascularForecaster:
    DOMAIN = "cardiovascular"

    @staticmethod
    def forecast(context: dict, window: str) -> dict:
        current_signals = context.get("wearable_signals", {}).get("current", {})
        latest_health = context.get("latest_health_payload", {})
        category = (latest_health.get("category_scores") or {}).get("cardiovascular_score", {})
        score_history = [100.0 - float(value) for value in context.get("category_histories", {}).get("cardiovascular_score", [])]
        current_risk = 100.0 - _safe_float(category.get("score"), 76.0)
        baseline = 100.0 - _safe_float(context.get("baseline_profile").reference_value("cardiovascular_score", 76.0), 76.0)
        contributors = [
            ProjectionContributor(
                label="resting heart rate",
                value=current_signals.get("resting_hr"),
                direction="higher"
                if _safe_float(current_signals.get("resting_hr"), 0.0) > _safe_float(context.get("baseline_profile").reference_value("resting_hr", 0.0), 0.0)
                else "stable",
                impact=0.34,
                detail="Persistent elevation can precede cardiovascular strain.",
            ),
            ProjectionContributor(
                label="blood pressure",
                value=f"{current_signals.get('blood_pressure_systolic')}/{current_signals.get('blood_pressure_diastolic')}",
                direction="higher",
                impact=0.28,
                detail="Recent blood-pressure burden affects projected cardiovascular drift.",
            ),
            ProjectionContributor(
                label="activity steps",
                value=current_signals.get("activity_steps"),
                direction="lower"
                if _safe_float(current_signals.get("activity_steps"), 0.0) < _safe_float(context.get("baseline_profile").reference_value("activity_steps", 0.0), 0.0)
                else "stable",
                impact=0.18,
                detail="Lower activity weakens projected recovery capacity.",
            ),
        ]
        explanation = "Based on resting heart rate, blood-pressure burden, and activity recovery patterns, cardiovascular drift may worsen if current trends persist."
        recommendation = "Favor recovery, hydration, and a lower-intensity load if the projected strain keeps climbing."
        return TemporalProjectionEngine.project(
            domain=CardiovascularForecaster.DOMAIN,
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
