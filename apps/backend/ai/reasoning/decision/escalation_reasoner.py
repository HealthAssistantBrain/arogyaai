from __future__ import annotations

from typing import Any

from ai.safety.policies.escalation_policy import EscalationPolicy

from ..schemas import NarrativeContext, ReasoningCard


class EscalationReasoner:
    def __init__(self) -> None:
        self.policy = EscalationPolicy()

    def assess(self, context: NarrativeContext, *, cards: list[ReasoningCard]) -> dict[str, Any]:
        emergency = bool(
            context.symptom_present("chest pain")
            or context.symptom_present("shortness of breath")
            or (context.metric("spo2") and (context.metric("spo2").current or 100) <= 92)
        )
        severe = "critical" if emergency else "high" if any(card.severity == "high" for card in cards) else "moderate" if cards else "low"
        resolution = self.policy.resolve(severity=severe, emergency_detected=emergency)
        return {
            "severity": severe,
            "emergency_detected": emergency,
            **resolution,
        }
