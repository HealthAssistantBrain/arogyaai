from __future__ import annotations

from ..core.temporal_projection_engine import TemporalProjectionEngine
from ..schemas.prediction_metadata import ProjectionContributor


class RecoveryInstability:
    NAME = "recovery_instability"

    @staticmethod
    def build(window: str, forecasts: dict[str, dict], trajectories: dict[str, dict]) -> dict:
        recovery = forecasts.get("recovery", {})
        sleep = forecasts.get("sleep", {})
        recovery_trajectory = trajectories.get("recovery_trajectory", {})
        current_value = (
            float(recovery.get("projected_risk") or 0.0) * 0.5
            + float(sleep.get("projected_risk") or 0.0) * 0.3
            + float(recovery_trajectory.get("projected_change") or 0.0) * 0.2
        )
        contributors = [
            ProjectionContributor(label="recovery risk", value=recovery.get("projected_risk"), direction=recovery.get("direction") or "stable", impact=0.4, detail="Projected recovery softness is the main instability driver."),
            ProjectionContributor(label="sleep instability", value=sleep.get("projected_risk"), direction=sleep.get("direction") or "stable", impact=0.26, detail="Sleep variability often destabilizes recovery."), 
        ]
        return TemporalProjectionEngine.project(
            domain=RecoveryInstability.NAME,
            window=window,
            current_value=current_value,
            history=[current_value, float(recovery_trajectory.get("projected_change") or current_value)],
            baseline_value=26.0,
            higher_is_better=False,
            contributors=contributors,
            explanation_hint="Recovery instability may persist when sleep and autonomic recovery remain inconsistent together.",
            recommendation="Favor consistency over intensity while projected instability is elevated.",
            source_count=3,
        ).model_dump()
