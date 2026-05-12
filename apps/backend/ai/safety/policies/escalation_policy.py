from __future__ import annotations


class EscalationPolicy:
    def resolve(self, *, severity: str, emergency_detected: bool, medication_blocked: bool = False) -> dict[str, object]:
        level = "none"
        clinician = False
        if emergency_detected or severity == "critical":
            level = "emergency"
            clinician = True
        elif severity == "high":
            level = "urgent_care"
            clinician = True
        elif severity == "moderate" or medication_blocked:
            level = "clinician_review"
            clinician = True
        return {
            "escalation_level": level,
            "clinician_escalation_recommended": clinician,
        }
