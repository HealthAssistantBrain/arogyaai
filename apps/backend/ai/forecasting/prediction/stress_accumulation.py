from __future__ import annotations

from ..core.temporal_projection_engine import TemporalProjectionEngine
from ..schemas.prediction_metadata import ProjectionContributor


class StressAccumulation:
    NAME = "stress_accumulation"

    @staticmethod
    def build(window: str, forecasts: dict[str, dict], trajectories: dict[str, dict]) -> dict:
        stress = forecasts.get("stress", {})
        cardio = forecasts.get("cardiovascular", {})
        drift = trajectories.get("behavioral_drift_projection", {})
        current_value = (
            float(stress.get("projected_risk") or 0.0) * 0.55
            + float(cardio.get("projected_risk") or 0.0) * 0.25
            + float(drift.get("projected_change") or 0.0) * 0.2
        )
        contributors = [
            ProjectionContributor(label="stress projection", value=stress.get("projected_risk"), direction=stress.get("direction") or "stable", impact=0.42, detail="Primary projected stress load."),
            ProjectionContributor(label="cardiovascular strain", value=cardio.get("projected_risk"), direction=cardio.get("direction") or "stable", impact=0.22, detail="Cardiovascular load can compound stress burden."),
            ProjectionContributor(label="behavioral drift", value=drift.get("projected_change"), direction=drift.get("direction") or "stable", impact=0.16, detail="Behavioral drift can make recovery less reliable."),
        ]
        return TemporalProjectionEngine.project(
            domain=StressAccumulation.NAME,
            window=window,
            current_value=current_value,
            history=[current_value, float(stress.get("projected_risk") or current_value)],
            baseline_value=28.0,
            higher_is_better=False,
            contributors=contributors,
            explanation_hint="Projected stress accumulation reflects sustained physiologic load rather than a single acute spike.",
            recommendation="Interrupt cumulative stress with sleep protection, workload pacing, and re-check if symptoms worsen.",
            source_count=3,
        ).model_dump()
