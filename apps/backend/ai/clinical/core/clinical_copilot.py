from __future__ import annotations

from typing import Any

from ai.safety.core.validator_engine import ValidatorEngine
from ai.safety.policies.escalation_policy import EscalationPolicy
from ai.safety.policies.provider_policy import ProviderPolicy
from ai.safety.validators.diagnosis_guard import DiagnosisGuard
from ai.safety.validators.hallucination_guard import HallucinationGuard

from ..copilot import ProviderAssistant
from ..utils import safe_float, safe_text, structured_log


class ClinicalCopilot:
    def __init__(self) -> None:
        self.assistant = ProviderAssistant()
        self.validator = ValidatorEngine()
        self.hallucination_guard = HallucinationGuard()
        self.diagnosis_guard = DiagnosisGuard()
        self.provider_policy = ProviderPolicy()
        self.escalation_policy = EscalationPolicy()

    async def answer_query(self, query: str, *, intelligence_bundle: dict[str, Any]) -> dict[str, Any]:
        raw = self.assistant.respond(query, intelligence_bundle)
        return self._apply_safety(query, raw, intelligence_bundle)

    def _apply_safety(self, query: str, payload: dict[str, Any], intelligence_bundle: dict[str, Any]) -> dict[str, Any]:
        patient = intelligence_bundle.get("patient") if isinstance(intelligence_bundle.get("patient"), dict) else {}
        risk_summary = intelligence_bundle.get("risk_summary") if isinstance(intelligence_bundle.get("risk_summary"), dict) else {}
        severity = safe_text(risk_summary.get("severity"), "moderate").lower()
        provider_policy = self.provider_policy.resolve("deterministic_fallback", degraded=False, fallback_used=False)

        validated = self.validator.validate(
            payload=payload,
            workflow="clinical_copilot",
            channel="provider_intelligence",
            provider="deterministic_fallback",
            query=query,
        )
        guarded = self.hallucination_guard.apply(validated.sanitized_payload, policy={"is_ocr": False})
        diagnosed = self.diagnosis_guard.apply(guarded["payload"], policy={"is_ocr": False})
        final_payload = diagnosed["payload"] if isinstance(diagnosed.get("payload"), dict) else payload

        confidence = min(
            safe_float(final_payload.get("confidence"), 0.72) or 0.72,
            safe_float(provider_policy.get("confidence_cap"), 0.58) or 0.58,
        )
        emergency = bool(risk_summary.get("escalation_candidate")) and severity == "critical"
        escalation = self.escalation_policy.resolve(
            severity=severity,
            emergency_detected=emergency,
            medication_blocked=False,
        )
        disclaimer = (
            "This provider-facing synthesis is grounded in the currently available longitudinal record and should be reviewed alongside the source chart."
            if provider_policy.get("force_clinician_disclaimer")
            else ""
        )

        safety = validated.metadata.as_dict()
        safety["hallucination_guard"] = {
            "flags": guarded.get("flags") or [],
            "risk": guarded.get("hallucination_risk"),
            "modified": guarded.get("modified"),
        }
        safety["diagnosis_guard"] = {
            "flags": diagnosed.get("flags") or [],
            "modified": diagnosed.get("modified"),
        }
        safety["provider_policy"] = provider_policy
        safety["disclaimer"] = disclaimer

        final_payload["confidence"] = round(confidence, 4)
        final_payload["escalation"] = escalation
        final_payload["safety"] = safety
        if disclaimer:
            final_payload["disclaimer"] = disclaimer
        structured_log(
            "[PROVIDER_QUERY]",
            patient_id=safe_text(patient.get("id")),
            intent=safe_text(final_payload.get("intent")),
            severity=severity,
        )
        return final_payload


_COPILOT: ClinicalCopilot | None = None


def get_clinical_copilot() -> ClinicalCopilot:
    global _COPILOT
    if _COPILOT is None:
        _COPILOT = ClinicalCopilot()
    return _COPILOT
