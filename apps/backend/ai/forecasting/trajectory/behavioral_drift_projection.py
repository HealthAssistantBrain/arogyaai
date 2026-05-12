from __future__ import annotations

from ..schemas.trajectory_response import TrajectoryResponse


class BehavioralDriftProjection:
    NAME = "behavioral_drift_projection"

    @staticmethod
    def build(window: str, forecasts: dict[str, dict], context: dict) -> dict:
        feature_snapshot = context.get("feature_snapshot", {})
        baseline = context.get("baseline_profile")
        steps = float(feature_snapshot.get("activity_level") or 0.0)
        baseline_steps = float(baseline.reference_value("activity_steps", steps) or steps or 1.0)
        sleep = float(feature_snapshot.get("sleep_duration") or 0.0)
        baseline_sleep = float(baseline.reference_value("sleep_hours", sleep) or sleep or 1.0)
        step_drift = ((steps - baseline_steps) / max(abs(baseline_steps), 1.0)) * 100.0
        sleep_drift = ((sleep - baseline_sleep) / max(abs(baseline_sleep), 1.0)) * 100.0
        drift_load = abs(step_drift) * 0.45 + abs(sleep_drift) * 0.55
        direction = "drifting" if drift_load >= 10 else "stable"
        severity = "moderate" if drift_load >= 18 else "low"
        selected = [forecasts[name] for name in ("sleep", "stress", "recovery") if name in forecasts]
        confidence = round(sum(float(item.get("confidence") or 0.0) for item in selected) / max(1, len(selected)), 4)
        return TrajectoryResponse(
            name=BehavioralDriftProjection.NAME,
            window=window,
            direction=direction,
            severity=severity,
            summary="Behavioral drift is estimated from movement and sleep changes relative to personal baseline.",
            projected_change=round(drift_load, 4),
            confidence=confidence,
            uncertainty=round(1.0 - confidence, 4),
            projection_strength=round(min(1.0, drift_load / 35.0), 4),
            signal_quality=round(confidence, 4),
            stability=round(sum(float(item.get("stability") or 0.0) for item in selected) / max(1, len(selected)), 4),
            supporting_domains=[item.get("domain") for item in selected if item.get("domain")],
            metadata={
                "step_drift_percent": round(step_drift, 4),
                "sleep_drift_percent": round(sleep_drift, 4),
            },
        ).model_dump()
