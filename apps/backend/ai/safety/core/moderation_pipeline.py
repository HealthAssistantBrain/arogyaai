from __future__ import annotations

import logging
from typing import Any

from ..classifiers import EmergencyClassifier, RiskClassifier, SafetyScoreClassifier
from ..policies import EscalationPolicy, ProviderPolicy, ResponsePolicy
from ..schemas import SafetyMetadata, ValidationResult
from ..validators import (
    DiagnosisGuard,
    DisclaimerEngine,
    EmergencyGuard,
    HallucinationGuard,
    MedicationGuard,
    ToneValidator,
)

logger = logging.getLogger("uvicorn.error")


class ModerationPipeline:
    def __init__(self) -> None:
        self.response_policy = ResponsePolicy()
        self.provider_policy = ProviderPolicy()
        self.escalation_policy = EscalationPolicy()
        self.emergency_classifier = EmergencyClassifier()
        self.risk_classifier = RiskClassifier()
        self.safety_score = SafetyScoreClassifier()
        self.hallucination_guard = HallucinationGuard()
        self.diagnosis_guard = DiagnosisGuard()
        self.medication_guard = MedicationGuard()
        self.emergency_guard = EmergencyGuard()
        self.tone_validator = ToneValidator()
        self.disclaimer_engine = DisclaimerEngine()

    def run(
        self,
        *,
        payload: dict[str, Any],
        workflow: str,
        channel: str,
        provider: str,
        query: str = "",
        conversation_history: list[dict[str, Any]] | None = None,
        degraded_mode: bool = False,
        fallback_used: bool = False,
    ) -> ValidationResult:
        policy = self.response_policy.policy_for(workflow, payload=payload)
        provider_policy = self.provider_policy.resolve(provider, degraded=degraded_mode, fallback_used=fallback_used)
        working = dict(payload or {})
        text = self.hallucination_guard.sanitizer.collect_text(working, policy=policy)
        emergency = self.emergency_classifier.classify(
            query=query,
            text=text,
            conversation_history=conversation_history,
        )

        hallucination = self.hallucination_guard.apply(working, policy=policy)
        working = hallucination["payload"]

        diagnosis = self.diagnosis_guard.apply(working, policy=policy)
        working = diagnosis["payload"]

        medication = self.medication_guard.apply(working, policy=policy)
        working = medication["payload"]

        tone = self.tone_validator.apply(working, policy=policy)
        working = tone["payload"]

        emergency_message = self.emergency_classifier.escalation_message(str(emergency.get("tier") or "general"))
        emergency_result = self.emergency_guard.apply(
            working,
            emergency=emergency,
            emergency_message=emergency_message,
        )
        working = emergency_result["payload"]

        disclaimers = self.disclaimer_engine.build(
            workflow=workflow,
            policy=policy,
            provider_policy=provider_policy,
            severity="critical" if emergency.get("detected") else "low",
            emergency_detected=bool(emergency.get("detected")),
            medication_blocked=bool(medication.get("blocked")),
            hallucination_risk=float(hallucination.get("hallucination_risk") or 0.0),
        )
        risk = self.risk_classifier.classify(
            emergency_detected=bool(emergency.get("detected")),
            hallucination_risk=float(hallucination.get("hallucination_risk") or 0.0),
            medication_blocked=bool(medication.get("blocked")),
            disclaimer_count=len(disclaimers),
            provider_multiplier=float(provider_policy.get("risk_multiplier") or 1.0),
            degraded_mode=degraded_mode,
        )
        disclaimers = self.disclaimer_engine.build(
            workflow=workflow,
            policy=policy,
            provider_policy=provider_policy,
            severity=str(risk["severity"]),
            emergency_detected=bool(emergency.get("detected")),
            medication_blocked=bool(medication.get("blocked")),
            hallucination_risk=float(hallucination.get("hallucination_risk") or 0.0),
        )
        working = self.disclaimer_engine.apply(working, disclaimers)
        escalation = self.escalation_policy.resolve(
            severity=str(risk["severity"]),
            emergency_detected=bool(emergency.get("detected")),
            medication_blocked=bool(medication.get("blocked")),
        )
        response_modified = any(
            bool(result.get("modified"))
            for result in (hallucination, diagnosis, medication, tone, emergency_result)
        )
        safety_score = self.safety_score.score(
            hallucination_risk=float(hallucination.get("hallucination_risk") or 0.0),
            response_modified=response_modified,
            disclaimer_count=len(disclaimers),
            emergency_detected=bool(emergency.get("detected")),
            degraded_mode=degraded_mode,
        )
        flags: list[str] = []
        blocked_categories: list[str] = []
        for result in (hallucination, diagnosis, medication, tone, emergency_result):
            for flag in result.get("flags", []):
                if flag and flag not in flags:
                    flags.append(str(flag))
        if medication.get("blocked"):
            blocked_categories.append("medication")
        metadata = SafetyMetadata(
            workflow=workflow,
            channel=channel,
            provider=provider,
            severity=str(risk["severity"]),
            escalation_level=str(escalation["escalation_level"]),
            safety_score=safety_score,
            hallucination_risk=float(hallucination.get("hallucination_risk") or 0.0),
            emergency_detected=bool(emergency.get("detected")),
            disclaimer_applied=list(disclaimers),
            response_modified=response_modified,
            clinician_escalation_recommended=bool(escalation["clinician_escalation_recommended"]),
            validation_flags=flags,
            warnings=[
                warning
                for warning in (
                    "provider_strict_mode" if provider_policy.get("provider_risk") == "strict" else "",
                    "degraded_mode_response" if degraded_mode or fallback_used else "",
                )
                if warning
            ],
            emergency_flags=[str(item) for item in emergency.get("matches", [])],
            blocked_categories=blocked_categories,
            provider_risk=str(provider_policy.get("provider_risk") or "standard"),
            degraded_mode=bool(degraded_mode or fallback_used),
        )
        safe = metadata.severity in {"low", "moderate"} and not metadata.failure_safe_triggered
        if metadata.emergency_detected:
            logger.warning(
                "[EMERGENCY DETECTED] workflow=%s channel=%s provider=%s matches=%s",
                workflow,
                channel,
                provider,
                metadata.emergency_flags,
            )
        if medication.get("blocked") or hallucination.get("flags"):
            logger.warning(
                "[HALLUCINATION BLOCKED] workflow=%s channel=%s provider=%s flags=%s",
                workflow,
                channel,
                provider,
                flags,
            )
        if disclaimers:
            logger.info(
                "[DISCLAIMER APPLIED] workflow=%s channel=%s count=%s",
                workflow,
                channel,
                len(disclaimers),
            )
        logger.info(
            "[AI SAFETY] workflow=%s channel=%s provider=%s severity=%s safety_score=%.2f emergency=%s modified=%s",
            workflow,
            channel,
            provider,
            metadata.severity,
            metadata.safety_score,
            metadata.emergency_detected,
            metadata.response_modified,
        )
        return ValidationResult(
            original_payload=dict(payload or {}),
            sanitized_payload=working,
            metadata=metadata,
            safe=safe,
            reason="centralized_ai_safety_validation",
        )
