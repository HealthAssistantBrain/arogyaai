from __future__ import annotations

from ..schemas.trajectory_response import TrajectoryResponse


class DeteriorationTrajectory:
    NAME = "deterioration_trajectory"
    DOMAINS = ("cardiovascular", "metabolic", "stress", "respiratory")

    @staticmethod
    def build(window: str, forecasts: dict[str, dict]) -> dict:
        selected = [forecasts[name] for name in DeteriorationTrajectory.DOMAINS if name in forecasts]
        if not selected:
            return TrajectoryResponse(
                name=DeteriorationTrajectory.NAME,
                window=window,
                direction="stable",
                severity="low",
                summary="Insufficient data for deterioration trajectory.",
            ).model_dump()
        mean_risk = sum(float(item.get("projected_risk") or 0.0) for item in selected) / len(selected)
        direction = "deteriorating" if mean_risk >= 45 else "stable" if mean_risk < 30 else "watch"
        severity = "high" if mean_risk >= 60 else "moderate" if mean_risk >= 40 else "low"
        return TrajectoryResponse(
            name=DeteriorationTrajectory.NAME,
            window=window,
            direction=direction,
            severity=severity,
            summary="Projected deterioration risk is driven by multi-domain physiologic strain rather than a single isolated metric.",
            projected_change=round(mean_risk, 4),
            confidence=round(sum(float(item.get("confidence") or 0.0) for item in selected) / len(selected), 4),
            uncertainty=round(sum(float(item.get("uncertainty") or 0.0) for item in selected) / len(selected), 4),
            projection_strength=round(sum(float(item.get("projection_strength") or 0.0) for item in selected) / len(selected), 4),
            signal_quality=round(sum(float(item.get("signal_quality") or 0.0) for item in selected) / len(selected), 4),
            stability=round(sum(float(item.get("stability") or 0.0) for item in selected) / len(selected), 4),
            supporting_domains=[item.get("domain") for item in selected if item.get("domain")],
            metadata={"mean_projected_risk": round(mean_risk, 4)},
        ).model_dump()
