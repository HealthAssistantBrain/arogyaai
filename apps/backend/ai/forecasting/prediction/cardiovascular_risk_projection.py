from __future__ import annotations

from ..core.temporal_projection_engine import TemporalProjectionEngine
from ..schemas.prediction_metadata import ProjectionContributor


class CardiovascularRiskProjection:
    NAME = "cardiovascular_risk_projection"

    @staticmethod
    def build(window: str, forecasts: dict[str, dict], trajectories: dict[str, dict]) -> dict:
        cardio = forecasts.get("cardiovascular", {})
        metabolic = forecasts.get("metabolic", {})
        anomaly = trajectories.get("anomaly_progression", {})
        current_value = (
            float(cardio.get("projected_risk") or 0.0) * 0.55
            + float(metabolic.get("projected_risk") or 0.0) * 0.25
            + float(anomaly.get("projected_change") or 0.0) * 0.2
        )
        contributors = [
            ProjectionContributor(label="cardiovascular drift", value=cardio.get("projected_risk"), direction=cardio.get("direction") or "stable", impact=0.44, detail="Projected cardiovascular drift is the main signal."),
            ProjectionContributor(label="metabolic instability", value=metabolic.get("projected_risk"), direction=metabolic.get("direction") or "stable", impact=0.2, detail="Metabolic pressure can amplify longer-horizon strain."),
            ProjectionContributor(label="anomaly progression", value=anomaly.get("projected_change"), direction=anomaly.get("direction") or "stable", impact=0.18, detail="Persisting anomalies lower forecast confidence and raise vigilance."),
        ]
        return TemporalProjectionEngine.project(
            domain=CardiovascularRiskProjection.NAME,
            window=window,
            current_value=current_value,
            history=[current_value, float(cardio.get("projected_risk") or current_value)],
            baseline_value=25.0,
            higher_is_better=False,
            contributors=contributors,
            explanation_hint="Projected cardiovascular risk combines direct strain, metabolic context, and anomaly persistence.",
            recommendation="If this projection stays elevated or symptoms appear, a clinician review is more appropriate than watchful waiting alone.",
            source_count=3,
        ).model_dump()
