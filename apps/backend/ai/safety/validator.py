from __future__ import annotations

import asyncio
import logging
import re
import time

from .clinical_rules import RAG_MIN_CONFIDENCE_THRESHOLD
from .confidence_scoring import compute_confidence
from .contradiction_checker import check_contradictions
from .emergency_escalation import scan_for_emergency
from .hallucination_detector import detect_hallucinations
from .medical_boundaries import apply_certainty_softening, check_medical_boundaries
from .response_rewriter import rewrite_response
from .risk_classifier import classify_risk
from .safety_types import ConversationContext, RiskLevel, ValidationFlag, ValidationResult

logger = logging.getLogger("arogyaai.safety.validator")

_SAFE_FALLBACK_RESPONSE = (
    "I want to make sure I give you the safest guidance possible. Based on what you've shared, "
    "I recommend speaking with a healthcare professional who can assess this properly."
)
_CASUAL_EXCHANGE_PATTERN = re.compile(
    r"\b(hi|hello|hey|thanks|thank you|bye|good morning|good evening|how are you|ok|okay)\b",
    re.IGNORECASE,
)


async def validate_response(
    user_input: str,
    ai_response: str,
    context: ConversationContext,
) -> ValidationResult:
    start_time = time.perf_counter()
    flags: list[ValidationFlag] = []
    stages: list[str] = []

    try:
        stages.append("emergency_scan")
        emergency = scan_for_emergency(user_input, ai_response, context)
        if emergency.is_emergency:
            flags.append(ValidationFlag.EMERGENCY_CONDITION)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return ValidationResult(
                original_response=ai_response,
                final_response=emergency.override_response or _SAFE_FALLBACK_RESPONSE,
                risk_level=RiskLevel.EMERGENCY,
                flags=flags,
                confidence_score=1.0,
                confidence_reason="Emergency override triggered. A direct escalation template was served.",
                escalation_required=True,
                escalation_message=emergency.override_response,
                processing_time_ms=elapsed_ms,
                pipeline_stages=stages,
                rewritten=True,
            )

        if (
            _CASUAL_EXCHANGE_PATTERN.search(user_input or "")
            and not context.user_symptoms
            and not context.vitals
            and not context.ml_predictions
            and not context.rag_evidence
        ):
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return ValidationResult(
                original_response=ai_response,
                final_response=ai_response,
                risk_level=RiskLevel.SAFE,
                flags=[],
                confidence_score=0.85,
                confidence_reason="Low-risk conversational exchange with no medical safety signals detected.",
                escalation_required=False,
                processing_time_ms=elapsed_ms,
                pipeline_stages=stages + ["casual_bypass"],
                rewritten=False,
            )

        async def _run_hallucination():
            return detect_hallucinations(ai_response, context)

        async def _run_contradiction():
            return check_contradictions(ai_response, context)

        async def _run_boundaries():
            return check_medical_boundaries(ai_response)

        stages.extend(["hallucination_detection", "contradiction_check", "medical_boundary_check"])
        hallucination, contradiction, boundary_result = await asyncio.gather(
            _run_hallucination(),
            _run_contradiction(),
            _run_boundaries(),
        )
        boundary_violation, boundary_details = boundary_result

        softened, certainty_changed = apply_certainty_softening(ai_response)
        if certainty_changed:
            flags.append(ValidationFlag.FAKE_CERTAINTY)
            flags.append(ValidationFlag.FORBIDDEN_PHRASE)
        if hallucination.detected and hallucination.severity in {"moderate", "severe"}:
            flags.append(ValidationFlag.HALLUCINATION_DETECTED)
        if hallucination.fabricated_claims or hallucination.unsupported_phrases:
            flags.append(ValidationFlag.UNSUPPORTED_DIAGNOSIS)
        if hallucination.rag_coverage < RAG_MIN_CONFIDENCE_THRESHOLD:
            flags.append(ValidationFlag.LOW_RAG_GROUNDING)
        if contradiction.detected:
            flags.append(ValidationFlag.CONTRADICTION_DETECTED)
        if boundary_violation:
            flags.append(ValidationFlag.UNSAFE_MEDICATION_ADVICE)
            if any("mg" in detail.lower() or "dose" in detail.lower() for detail in boundary_details):
                flags.append(ValidationFlag.OVERDOSE_RISK)

        stages.append("confidence_scoring")
        confidence = compute_confidence(context, hallucination, contradiction)

        stages.append("risk_classification")
        risk_level = classify_risk(emergency, hallucination, contradiction, confidence, context)

        stages.append("response_rewriting")
        needs_rewrite = bool(flags) or risk_level is not RiskLevel.SAFE or confidence.score < 0.60 or softened != ai_response
        if needs_rewrite:
            final_response, rewritten = rewrite_response(
                ai_response,
                risk_level,
                hallucination,
                confidence,
                list(dict.fromkeys(flags)),
            )
        else:
            final_response, rewritten = ai_response, False

        escalation_required = risk_level in {RiskLevel.URGENT, RiskLevel.EMERGENCY}
        escalation_message = None
        if escalation_required:
            escalation_message = (
                "Based on the severity of the available signals, please seek prompt medical attention."
                if risk_level == RiskLevel.URGENT
                else final_response
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return ValidationResult(
            original_response=ai_response,
            final_response=final_response,
            risk_level=risk_level,
            flags=list(dict.fromkeys(flags)),
            confidence_score=confidence.score,
            confidence_reason=confidence.reason,
            uncertainty_flags=confidence.uncertainty_flags,
            rewritten=rewritten,
            escalation_required=escalation_required,
            escalation_message=escalation_message,
            processing_time_ms=elapsed_ms,
            pipeline_stages=stages,
        )
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.critical(
            "Safety pipeline crashed. Serving fallback response.",
            exc_info=True,
            extra={"user_id": context.user_id, "error": str(exc)},
        )
        return ValidationResult(
            original_response=ai_response,
            final_response=_SAFE_FALLBACK_RESPONSE,
            risk_level=RiskLevel.ELEVATED,
            flags=[ValidationFlag.HALLUCINATION_DETECTED],
            confidence_score=0.0,
            confidence_reason="Safety pipeline failure. Conservative fallback served.",
            rewritten=True,
            processing_time_ms=elapsed_ms,
            pipeline_stages=stages,
        )
