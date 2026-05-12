from __future__ import annotations

from ai.safety.policies.escalation_policy import EscalationPolicy

from ..utils import clinical_severity, safe_dict, safe_list


class EscalationManager:
    def __init__(self) -> None:
        self.policy = EscalationPolicy()

    def resolve(self, monitoring_state: dict, deterioration_projection: dict) -> dict:
        signals = safe_list(safe_dict(monitoring_state).get("signals"))
        overall_risk = float(safe_dict(monitoring_state).get("overall_risk") or 0.0)
        risk_72h = float(safe_dict(safe_dict(deterioration_projection).get("horizons")).get("72h", {}).get("projected_risk") or overall_risk)
        persistent = max((float(safe_dict(item).get("persistence_days") or 0.0) for item in signals), default=0.0)
        accelerating = max((float(safe_dict(item).get("acceleration") or 0.0) for item in signals), default=0.0)

        if overall_risk >= 88.0 or (risk_72h >= 85.0 and persistent >= 3.0 and accelerating >= 2.0):
            level = "escalate"
        elif overall_risk >= 70.0 or risk_72h >= 75.0:
            level = "intervene"
        elif overall_risk >= 45.0:
            level = "monitor"
        else:
            level = "reassure"

        severity = clinical_severity(max(overall_risk, risk_72h))
        policy = self.policy.resolve(
            severity=severity,
            emergency_detected=level == "escalate",
        )
        return {
            "level": level,
            "policy": policy,
            "reason": (
                "Rapid risk acceleration and persistence justify stronger escalation."
                if level in {"intervene", "escalate"}
                else "The pattern is notable but does not currently justify aggressive escalation."
            ),
            "review_in_hours": 6 if level == "escalate" else 12 if level == "intervene" else 24 if level == "monitor" else 48,
            "should_notify": level != "reassure",
        }
