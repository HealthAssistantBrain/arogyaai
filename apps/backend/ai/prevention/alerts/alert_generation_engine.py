from __future__ import annotations

from ..schemas import PreventiveAlert
from ..utils import safe_dict, safe_list, safe_text, severity_from_score, slugify
from .severity_routing import SeverityRouting


class AlertGenerationEngine:
    @staticmethod
    def generate(monitoring_state: dict, intervention_plan: dict, guidance: dict, escalation: dict) -> list[dict]:
        alerts: list[dict] = []
        for signal_payload in safe_list(safe_dict(monitoring_state).get("signals"))[:3]:
            signal = safe_dict(signal_payload)
            severity = severity_from_score(float(signal.get("risk_score") or 0.0))
            routing = SeverityRouting.route(severity, str(safe_dict(escalation).get("level") or "monitor"))
            alerts.append(
                PreventiveAlert(
                    alert_id=f"{slugify(str(signal.get('signal_id') or signal.get('domain') or 'alert'))}-alert",
                    title=f"{safe_text(signal.get('domain'), 'Health').replace('_', ' ').title()} needs preventive attention",
                    message=safe_text(signal.get("summary"), "A preventive follow-up signal was detected."),
                    severity=severity,
                    domain=safe_text(signal.get("domain"), "general"),
                    escalation_level=safe_text(safe_dict(escalation).get("level"), "monitor"),
                    notification_class=str(routing.get("notification_class") or "digest"),
                    rationale=[safe_text(signal.get("summary"))],
                    guidance=safe_list(signal.get("recommended_actions"))[:2],
                    metadata={"channel": routing.get("channel"), "cadence_minutes": routing.get("cadence_minutes")},
                ).model_dump(mode="json")
            )

        if not alerts:
            alerts.append(
                PreventiveAlert(
                    alert_id="preventive-monitoring-stable",
                    title="Preventive monitoring remains active",
                    message=safe_text(safe_dict(guidance).get("summary"), "No high-priority preventive alert is active right now."),
                    severity="info",
                    domain="general",
                    escalation_level="reassure",
                    notification_class="digest",
                ).model_dump(mode="json")
            )
        return alerts
