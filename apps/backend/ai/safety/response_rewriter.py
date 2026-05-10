from __future__ import annotations

import logging
import re

from .medical_boundaries import apply_certainty_softening, strip_medication_instructions
from .safety_types import ConfidenceReport, HallucinationReport, RiskLevel, ValidationFlag

logger = logging.getLogger("arogyaai.safety.rewriter")

_ESCALATION_APPENDS = {
    RiskLevel.URGENT: (
        "\n\n⚕️ Important: Given what you've shared, I'd strongly recommend getting a clinical evaluation soon, ideally today or tomorrow. "
        "These signs are worth taking seriously."
    ),
    RiskLevel.ELEVATED: (
        "\n\n💡 Worth noting: I'd encourage you to bring these findings to your doctor at your next visit, or sooner if anything changes."
    ),
    RiskLevel.CAUTION: (
        "\n\nThis assessment is based on the information shared and should be discussed with a healthcare provider for confirmation."
    ),
}

_LOW_CONFIDENCE_CAVEAT = (
    "\n\nNote: This response is based on limited available data and carries meaningful uncertainty. "
    "Please treat it as general guidance, not a clinical assessment."
)

_STAT_STRIP_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*%\s+(?:chance|risk|probability|likelihood|of patients?)\b[^.]*\.",
    re.IGNORECASE,
)


def rewrite_response(
    text: str,
    risk_level: RiskLevel,
    hallucination: HallucinationReport,
    confidence: ConfidenceReport,
    flags: list[ValidationFlag],
) -> tuple[str, bool]:
    try:
        modified = text or ""
        any_change = False

        modified, changed = apply_certainty_softening(modified)
        any_change = any_change or changed

        if ValidationFlag.UNSAFE_MEDICATION_ADVICE in flags:
            modified, changed = strip_medication_instructions(modified)
            any_change = any_change or changed

        if hallucination.fabricated_claims:
            updated = _STAT_STRIP_PATTERN.sub(
                "[statistic omitted. There is not enough evidence in the current context to support this figure.]",
                modified,
            )
            if updated != modified:
                modified = updated
                any_change = True

        for phrase in hallucination.unsupported_phrases:
            if len(phrase) <= 5:
                continue
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            updated = pattern.sub(
                f"possible {phrase} (unconfirmed. Clinical evaluation is recommended)",
                modified,
                count=1,
            )
            if updated != modified:
                modified = updated
                any_change = True

        if risk_level in _ESCALATION_APPENDS:
            append_text = _ESCALATION_APPENDS[risk_level]
            if append_text not in modified:
                modified = modified.rstrip() + append_text
                any_change = True

        if confidence.score < 0.55 and risk_level not in {RiskLevel.EMERGENCY, RiskLevel.URGENT}:
            if _LOW_CONFIDENCE_CAVEAT not in modified:
                modified = modified.rstrip() + _LOW_CONFIDENCE_CAVEAT
                any_change = True

        return modified, any_change
    except Exception as exc:
        logger.error("Response rewriter failed: %s", exc, exc_info=True)
        return text, False
