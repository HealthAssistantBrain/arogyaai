from __future__ import annotations

from ..schemas.trajectory_response import TrajectoryResponse


class RecoveryTrajectory:
    NAME = "recovery_trajectory"
    DOMAINS = ("recovery", "sleep", "stress")

    @staticmethod
    def build(window: str, forecasts: dict[str, dict]) -> dict:
        selected = [forecasts[name] for name in RecoveryTrajectory.DOMAINS if name in forecasts]
        if not selected:
            return TrajectoryResponse(
                name=RecoveryTrajectory.NAME,
                window=window,
                direction="stable",
                severity="low",
                summary="Insufficient data for recovery trajectory.",
            ).model_dump()
        mean_recovery_risk = sum(float(item.get("projected_risk") or 0.0) for item in selected) / len(selected)
        direction = "improving" if mean_recovery_risk < 28 else "unstable" if mean_recovery_risk >= 42 else "stable"
        severity = "moderate" if mean_recovery_risk >= 42 else "low"
        return TrajectoryResponse(
            name=RecoveryTrajectory.NAME,
            window=window,
            direction=direction,
            severity=severity,
            summary="Recovery trajectory reflects how sleep quality, cumulative stress, and resilience are evolving together.",
            projected_change=round(100.0 - mean_recovery_risk, 4),
            confidence=round(sum(float(item.get("confidence") or 0.0) for item in selected) / len(selected), 4),
            uncertainty=round(sum(float(item.get("uncertainty") or 0.0) for item in selected) / len(selected), 4),
            projection_strength=round(sum(float(item.get("projection_strength") or 0.0) for item in selected) / len(selected), 4),
            signal_quality=round(sum(float(item.get("signal_quality") or 0.0) for item in selected) / len(selected), 4),
            stability=round(sum(float(item.get("stability") or 0.0) for item in selected) / len(selected), 4),
            supporting_domains=[item.get("domain") for item in selected if item.get("domain")],
            metadata={"mean_recovery_risk": round(mean_recovery_risk, 4)},
        ).model_dump()
