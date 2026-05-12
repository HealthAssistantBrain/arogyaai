from __future__ import annotations

from ..core.temporal_projection_engine import TemporalProjectionEngine
from ..schemas.prediction_metadata import ProjectionContributor


class FatiguePrediction:
    NAME = "fatigue_prediction"

    @staticmethod
    def build(window: str, forecasts: dict[str, dict], context: dict) -> dict:
        sleep = forecasts.get("sleep", {})
        stress = forecasts.get("stress", {})
        recovery = forecasts.get("recovery", {})
        risk_history = [
            float(value)
            for value in (
                sleep.get("projected_risk"),
                stress.get("projected_risk"),
                recovery.get("projected_risk"),
            )
            if value is not None
        ]
        current_value = sum(risk_history) / max(1, len(risk_history))
        contributors = [
            ProjectionContributor(label="sleep debt", value=sleep.get("projected_risk"), direction=sleep.get("direction") or "stable", impact=0.35, detail="Projected sleep deterioration increases fatigue load."),
            ProjectionContributor(label="stress accumulation", value=stress.get("projected_risk"), direction=stress.get("direction") or "stable", impact=0.33, detail="Sustained stress can accelerate fatigue."),
            ProjectionContributor(label="recovery consistency", value=recovery.get("projected_risk"), direction=recovery.get("direction") or "stable", impact=0.25, detail="Unstable recovery reduces resilience."),
        ]
        explanation = "Based on sleep debt, projected recovery softness, and stress load, fatigue risk may increase if current patterns continue."
        recommendation = "Reduce stacked exertion and prioritize consistent recovery inputs while projected fatigue remains elevated."
        return TemporalProjectionEngine.project(
            domain=FatiguePrediction.NAME,
            window=window,
            current_value=current_value,
            history=risk_history or [current_value],
            baseline_value=30.0,
            higher_is_better=False,
            contributors=contributors,
            explanation_hint=explanation,
            recommendation=recommendation,
            source_count=3,
        ).model_dump()
