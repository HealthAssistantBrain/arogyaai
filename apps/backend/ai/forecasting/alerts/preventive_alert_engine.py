from __future__ import annotations

from ..schemas.trajectory_response import PreventiveAlertResponse
from .escalation_forecasting import EscalationForecasting
from .threshold_warning_engine import ThresholdWarningEngine


class PreventiveAlertEngine:
    @staticmethod
    def build(window: str, forecasts: dict[str, dict], predictions: dict[str, dict]) -> list[dict]:
        alerts: list[dict] = []
        for payload in [*forecasts.values(), *predictions.values()]:
            projected_risk = float(payload.get("projected_risk") or 0.0)
            severity = ThresholdWarningEngine.severity_for(projected_risk)
            if severity == "low":
                continue
            direction = str(payload.get("direction") or "stable")
            alerts.append(
                PreventiveAlertResponse(
                    severity=severity,
                    title=f"Projected {str(payload.get('domain') or '').replace('_', ' ')} strain",
                    summary=str(payload.get("explanation") or "A projected health signal may worsen if the current pattern continues."),
                    window=window,
                    domain=str(payload.get("domain") or "general"),
                    recommendation=str(payload.get("recommendation") or "Monitor the trend and review the signal if it persists."),
                    escalation_level=EscalationForecasting.level_for(severity=severity, direction=direction),
                    metadata={
                        "projected_risk": projected_risk,
                        "confidence": payload.get("confidence"),
                    },
                ).model_dump()
            )
        return alerts
