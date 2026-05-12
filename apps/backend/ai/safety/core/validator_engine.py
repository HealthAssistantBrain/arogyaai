from __future__ import annotations

import logging
from typing import Any

from ..policies import ResponsePolicy
from ..schemas import SafetyMetadata, ValidationResult
from .moderation_pipeline import ModerationPipeline

logger = logging.getLogger("uvicorn.error")


class ValidatorEngine:
    def __init__(self) -> None:
        self.pipeline = ModerationPipeline()
        self.response_policy = ResponsePolicy()

    def validate(
        self,
        *,
        payload: dict[str, Any] | None,
        workflow: str,
        channel: str,
        provider: str,
        query: str = "",
        conversation_history: list[dict[str, Any]] | None = None,
        degraded_mode: bool = False,
        fallback_used: bool = False,
    ) -> ValidationResult:
        safe_payload = dict(payload or {})
        try:
            return self.pipeline.run(
                payload=safe_payload,
                workflow=workflow,
                channel=channel,
                provider=provider,
                query=query,
                conversation_history=conversation_history,
                degraded_mode=degraded_mode,
                fallback_used=fallback_used,
            )
        except Exception as exc:
            policy = self.response_policy.policy_for(workflow, payload=safe_payload)
            fallback_payload = self.response_policy.safe_fallback_payload(
                workflow,
                emergency=False,
                ocr=bool(policy.get("is_ocr")),
            )
            metadata = SafetyMetadata(
                workflow=workflow,
                channel=channel,
                provider=provider,
                severity="high",
                escalation_level="clinician_review",
                safety_score=0.1,
                hallucination_risk=1.0,
                emergency_detected=False,
                disclaimer_applied=["Please consult a clinician for diagnosis, treatment, or medication decisions."],
                response_modified=True,
                clinician_escalation_recommended=True,
                validation_flags=["validator_failure_safe"],
                warnings=["validator_crash_fallback"],
                provider_risk="maximum",
                degraded_mode=True,
                failure_safe_triggered=True,
            )
            fallback_payload["disclaimer"] = metadata.disclaimer_applied[0]
            fallback_payload["medical_disclaimer"] = metadata.disclaimer_applied[0]
            logger.exception(
                "[AI SAFETY] validator failed; serving fallback workflow=%s channel=%s provider=%s error=%s",
                workflow,
                channel,
                provider,
                exc,
            )
            return ValidationResult(
                original_payload=safe_payload,
                sanitized_payload=fallback_payload,
                metadata=metadata,
                safe=False,
                reason="validator_failure_safe",
            )
