from __future__ import annotations

from typing import Any


class DisclaimerEngine:
    def build(
        self,
        *,
        workflow: str,
        policy: dict[str, Any],
        provider_policy: dict[str, Any],
        severity: str,
        emergency_detected: bool,
        medication_blocked: bool,
        hallucination_risk: float,
    ) -> list[str]:
        disclaimers: list[str] = []
        if policy.get("is_ocr"):
            disclaimers.append(
                "This is a conservative summary of extracted report content. Extracted facts should be reviewed separately from AI interpretation."
            )
        if emergency_detected:
            disclaimers.append("This may be an emergency. Please seek immediate in-person or emergency care.")
        if medication_blocked:
            disclaimers.append("Medication selection, dosing, and treatment changes should be handled by a licensed clinician or pharmacist.")
        if severity in {"moderate", "high", "critical"} or hallucination_risk >= 0.12 or policy.get("is_ocr"):
            disclaimers.append("This is not a diagnosis and should not replace clinical evaluation.")
        if provider_policy.get("force_clinician_disclaimer") or severity in {"moderate", "high", "critical"}:
            disclaimers.append("Please consult a clinician for diagnosis, treatment, or medication decisions.")
        return list(dict.fromkeys(disclaimers))

    def apply(self, payload: dict[str, Any], disclaimers: list[str]) -> dict[str, Any]:
        if not disclaimers:
            return payload
        updated = dict(payload)
        updated["disclaimer"] = disclaimers[0]
        updated["medical_disclaimer"] = disclaimers[0]
        safety_notes = updated.get("safety_notes") if isinstance(updated.get("safety_notes"), list) else []
        for disclaimer in reversed(disclaimers):
            if disclaimer not in safety_notes:
                safety_notes.insert(0, disclaimer)
        updated["safety_notes"] = safety_notes[:4]
        return updated
