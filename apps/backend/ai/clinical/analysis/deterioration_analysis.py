from __future__ import annotations

from typing import Any

from ..utils import event_severity_rank, percent, risk_label, safe_float, safe_list, safe_text, structured_log


class DeteriorationAnalysis:
    @staticmethod
    def analyze(context: dict[str, Any], trend_analysis: dict[str, Any]) -> dict[str, Any]:
        patient = context.get("patient") if isinstance(context.get("patient"), dict) else {}
        alerts = safe_list(context.get("alerts"))
        risk_score = safe_float(patient.get("risk_score"), 0.0) or 0.0
        recent_alert_burden = sum(max(1, event_severity_rank(item.get("severity"))) for item in alerts[:6])
        deterioration_domains = [item.get("domain") for item in trend_analysis.get("deteriorating_metrics") or []]
        deterioration_domains = [safe_text(item) for item in deterioration_domains if safe_text(item)]
        forecast = context.get("forecasting") if isinstance(context.get("forecasting"), dict) else {}
        forecast_72h = forecast.get("forecast", {}).get("72h") if isinstance(forecast.get("forecast"), dict) else {}
        projected = 0.0
        if isinstance(forecast_72h, dict):
            projected = max(
                [safe_float(item.get("projected_risk"), 0.0) or 0.0 for item in safe_list(forecast_72h.get("domains"))]
                + [safe_float(item.get("projected_risk"), 0.0) or 0.0 for item in safe_list(forecast_72h.get("predictions"))]
                + [0.0]
            )

        score = min(
            100.0,
            (risk_score * 0.45)
            + (recent_alert_burden * 6.5)
            + (len(trend_analysis.get("deteriorating_metrics") or []) * 11.0)
            + (projected * 0.25),
        )
        severity = risk_label(score)
        escalation_recommended = severity in {"high", "critical"} or any(event_severity_rank(item.get("severity")) >= 4 for item in alerts)
        narrative = (
            "Longitudinal deterioration is being driven by "
            f"{', '.join(deterioration_domains[:3]) or 'recent risk escalation'} with forecasted strain over the next 72 hours."
        )
        structured_log(
            "[RISK_PRIORITIZATION]",
            patient_id=safe_text(patient.get("id")),
            deterioration_score=round(score, 1),
            escalation=escalation_recommended,
        )
        return {
            "score": round(score, 1),
            "severity": severity,
            "narrative": narrative,
            "projected_risk_72h": percent(projected, scale_if_fraction=False),
            "domains": deterioration_domains[:4],
            "recent_alert_burden": recent_alert_burden,
            "escalation_recommended": escalation_recommended,
            "recovery_failure_pattern": bool(
                severity in {"high", "critical"}
                and len(trend_analysis.get("deteriorating_metrics") or []) >= 2
                and len(alerts) >= 2
            ),
        }
