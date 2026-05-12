from __future__ import annotations

from ..alerts.preventive_alert_engine import PreventiveAlertEngine
from ..prediction.cardiovascular_risk_projection import CardiovascularRiskProjection
from ..prediction.fatigue_prediction import FatiguePrediction
from ..prediction.recovery_instability import RecoveryInstability
from ..prediction.stress_accumulation import StressAccumulation
from ..trajectory.anomaly_progression import AnomalyProgression
from ..trajectory.behavioral_drift_projection import BehavioralDriftProjection
from ..trajectory.deterioration_trajectory import DeteriorationTrajectory
from ..trajectory.recovery_trajectory import RecoveryTrajectory


class TrajectoryOrchestrator:
    @staticmethod
    def build(window: str, *, forecasts: dict[str, dict], context: dict) -> dict[str, list[dict] | dict[str, dict]]:
        trajectories = {
            "deterioration_trajectory": DeteriorationTrajectory.build(window, forecasts),
            "recovery_trajectory": RecoveryTrajectory.build(window, forecasts),
            "behavioral_drift_projection": BehavioralDriftProjection.build(window, forecasts, context),
            "anomaly_progression": AnomalyProgression.build(window, forecasts, context),
        }
        predictions = {
            "fatigue_prediction": FatiguePrediction.build(window, forecasts, context),
            "stress_accumulation": StressAccumulation.build(window, forecasts, trajectories),
            "recovery_instability": RecoveryInstability.build(window, forecasts, trajectories),
            "cardiovascular_risk_projection": CardiovascularRiskProjection.build(window, forecasts, trajectories),
        }
        alerts = PreventiveAlertEngine.build(window, forecasts, predictions)
        return {
            "trajectories": list(trajectories.values()),
            "predictions": list(predictions.values()),
            "alerts": alerts,
            "prediction_map": predictions,
            "trajectory_map": trajectories,
        }
