from __future__ import annotations

from ..schemas.trajectory_response import TrajectoryResponse


class AnomalyProgression:
    NAME = "anomaly_progression"

    @staticmethod
    def build(window: str, forecasts: dict[str, dict], context: dict) -> dict:
        anomalies = context.get("current_anomalies") or []
        severe = sum(1 for item in anomalies if str(item.get("severity") or "").lower() in {"high", "critical"})
        projected_risk = max((float(forecasts.get("stress", {}).get("projected_risk") or 0.0)), float(forecasts.get("cardiovascular", {}).get("projected_risk") or 0.0))
        direction = "worsening" if severe or projected_risk >= 48 else "stable"
        severity = "high" if severe >= 2 or projected_risk >= 60 else "moderate" if anomalies else "low"
        return TrajectoryResponse(
            name=AnomalyProgression.NAME,
            window=window,
            direction=direction,
            severity=severity,
            summary="Anomaly progression tracks whether current physiologic outliers are likely to persist or accelerate.",
            projected_change=round(projected_risk + severe * 8.0, 4),
            confidence=round(max(float(forecasts.get("stress", {}).get("confidence") or 0.0), float(forecasts.get("cardiovascular", {}).get("confidence") or 0.0)), 4),
            uncertainty=round(min(float(forecasts.get("stress", {}).get("uncertainty") or 1.0), float(forecasts.get("cardiovascular", {}).get("uncertainty") or 1.0)), 4),
            projection_strength=round(max(float(forecasts.get("stress", {}).get("projection_strength") or 0.0), float(forecasts.get("cardiovascular", {}).get("projection_strength") or 0.0)), 4),
            signal_quality=round(max(float(forecasts.get("stress", {}).get("signal_quality") or 0.0), float(forecasts.get("cardiovascular", {}).get("signal_quality") or 0.0)), 4),
            stability=round(min(float(forecasts.get("stress", {}).get("stability") or 1.0), float(forecasts.get("cardiovascular", {}).get("stability") or 1.0)), 4),
            supporting_domains=[name for name in ("stress", "cardiovascular") if forecasts.get(name)],
            metadata={"active_anomaly_count": len(anomalies), "high_severity_count": severe},
        ).model_dump()
