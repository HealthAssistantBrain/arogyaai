from __future__ import annotations

from ..schemas import PreventiveAlert
from ..utils import safe_dict, slugify


class EscalationAlerts:
    @staticmethod
    def build(escalation: dict, guidance: dict) -> list[dict]:
        escalation_level = str(safe_dict(escalation).get("level") or "monitor")
        if escalation_level not in {"intervene", "escalate"}:
            return []
        return [
            PreventiveAlert(
                alert_id=f"escalation-{slugify(escalation_level)}",
                title="Escalation threshold reached",
                message=str(safe_dict(escalation).get("reason") or safe_dict(guidance).get("summary") or "A higher-priority preventive response is justified."),
                severity="critical" if escalation_level == "escalate" else "warning",
                domain=str(safe_dict(guidance).get("focus_domain") or "general"),
                escalation_level=escalation_level,
                notification_class="urgent" if escalation_level == "escalate" else "near_real_time",
                rationale=[str(safe_dict(escalation).get("reason") or "")],
            ).model_dump(mode="json")
        ]
