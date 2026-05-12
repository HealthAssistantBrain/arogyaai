from __future__ import annotations

from typing import Any

from .contradiction_checker import check_contradictions
from .core.validator_engine import ValidatorEngine
from .safety_types import ConversationContext, RiskLevel, ValidationFlag, ValidationResult

_ENGINE = ValidatorEngine()
_FLAG_MAP = {
    "fake_certainty": ValidationFlag.FAKE_CERTAINTY,
    "fabricated_statistics": ValidationFlag.HALLUCINATION_DETECTED,
    "fake_reference": ValidationFlag.HALLUCINATION_DETECTED,
    "diagnosis_softened": ValidationFlag.UNSUPPORTED_DIAGNOSIS,
    "unsafe_medication_advice": ValidationFlag.UNSAFE_MEDICATION_ADVICE,
    "emergency_detected": ValidationFlag.EMERGENCY_CONDITION,
}


async def validate_response(
    user_input: str,
    ai_response: str,
    context: ConversationContext,
) -> ValidationResult:
    result = _ENGINE.validate(
        payload={"message": ai_response, "summary": ai_response},
        workflow="chatbot",
        channel="legacy_chat",
        provider=getattr(context.provider, "value", "unknown"),
        query=user_input,
        conversation_history=context.conversation_history,
    )
    metadata = result.metadata
    flags = _map_flags(metadata.validation_flags)
    contradiction = check_contradictions(ai_response, context)
    if contradiction.detected and ValidationFlag.CONTRADICTION_DETECTED not in flags:
        flags.append(ValidationFlag.CONTRADICTION_DETECTED)
    risk_level = _risk_level_from_metadata(metadata, contradiction_detected=contradiction.detected)
    final_response = result.final_text or ai_response
    return ValidationResult(
        original_response=ai_response,
        final_response=final_response,
        risk_level=risk_level,
        flags=flags,
        confidence_score=metadata.safety_score,
        confidence_reason=_confidence_reason(metadata),
        uncertainty_flags=list(metadata.disclaimer_applied),
        rewritten=metadata.response_modified,
        escalation_required=metadata.escalation_level in {"clinician_review", "urgent_care", "emergency"},
        escalation_message=final_response if metadata.emergency_detected else None,
        processing_time_ms=0.0,
        pipeline_stages=["central_validator_engine"],
    )


def _map_flags(raw_flags: list[str]) -> list[ValidationFlag]:
    mapped: list[ValidationFlag] = []
    for flag in raw_flags:
        enum_value = _FLAG_MAP.get(str(flag))
        if enum_value and enum_value not in mapped:
            mapped.append(enum_value)
    return mapped


def _risk_level_from_metadata(metadata: Any, *, contradiction_detected: bool = False) -> RiskLevel:
    severity = str(getattr(metadata, "severity", "low")).strip().lower()
    if getattr(metadata, "emergency_detected", False):
        return RiskLevel.EMERGENCY
    if contradiction_detected and severity in {"low", "moderate"}:
        return RiskLevel.ELEVATED
    if severity == "high":
        return RiskLevel.URGENT
    if severity == "moderate":
        return RiskLevel.ELEVATED
    if getattr(metadata, "response_modified", False) or getattr(metadata, "disclaimer_applied", []):
        return RiskLevel.CAUTION
    return RiskLevel.SAFE


def _confidence_reason(metadata: Any) -> str:
    if getattr(metadata, "emergency_detected", False):
        return "Emergency escalation messaging was applied."
    if getattr(metadata, "blocked_categories", []):
        return "Unsafe clinical directives were removed."
    if getattr(metadata, "response_modified", False):
        return "The response was moderated to reduce diagnostic certainty and improve safety."
    return "No major safety issues were detected."
