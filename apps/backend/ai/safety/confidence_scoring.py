from __future__ import annotations

import logging

from .safety_types import ConfidenceReport, ContradictionReport, ConversationContext, HallucinationReport

logger = logging.getLogger("arogyaai.safety.confidence")

_WEIGHTS = {
    "model_confidence": 0.25,
    "rag_match_quality": 0.25,
    "ml_prediction_score": 0.20,
    "symptom_completeness": 0.15,
    "contradiction_penalty": 0.10,
    "hallucination_penalty": 0.05,
}

_PENALTY_MAP = {
    "none": 0.00,
    "mild": 0.05,
    "moderate": 0.15,
    "severe": 0.30,
    "minor": 0.05,
    "major": 0.20,
    "critical": 0.40,
}


def compute_confidence(
    context: ConversationContext,
    hallucination: HallucinationReport,
    contradiction: ContradictionReport,
) -> ConfidenceReport:
    try:
        factors: dict[str, float] = {}
        uncertainty_flags: list[str] = []

        raw_confidence = context.raw_model_confidence
        if raw_confidence is not None:
            factors["model_confidence"] = min(1.0, max(0.0, float(raw_confidence)))
        else:
            provider_defaults = {"nvidia": 0.72, "ollama": 0.60, "openai": 0.70}
            factors["model_confidence"] = provider_defaults.get(context.provider.value, 0.65)
            uncertainty_flags.append("model_confidence_unavailable")

        factors["rag_match_quality"] = min(1.0, max(0.0, float(context.rag_confidence or 0.0)))
        if context.rag_confidence < 0.45:
            uncertainty_flags.append("weak_rag_grounding")
        if not context.rag_evidence:
            uncertainty_flags.append("no_rag_evidence_retrieved")
            factors["rag_match_quality"] = 0.2

        factors["ml_prediction_score"] = _extract_max_ml_confidence(context)
        if factors["ml_prediction_score"] < 0.4:
            uncertainty_flags.append("low_ml_prediction_confidence")

        symptom_count = len(context.user_symptoms)
        has_vitals = bool(context.vitals)
        completeness = min(1.0, (symptom_count / 5.0) * 0.7 + (0.3 if has_vitals else 0.0))
        factors["symptom_completeness"] = completeness
        if symptom_count == 0:
            uncertainty_flags.append("no_symptoms_provided")
        if not has_vitals:
            uncertainty_flags.append("no_vitals_available")

        hallucination_penalty = _PENALTY_MAP.get(hallucination.severity, 0.0)
        contradiction_penalty = _PENALTY_MAP.get(contradiction.severity, 0.0)
        factors["hallucination_penalty"] = -hallucination_penalty
        factors["contradiction_penalty"] = -contradiction_penalty

        if hallucination.detected:
            uncertainty_flags.append(f"hallucination_{hallucination.severity}")
        if contradiction.detected:
            uncertainty_flags.append(f"contradiction_{contradiction.severity}")

        positive_score = (
            factors["model_confidence"] * _WEIGHTS["model_confidence"]
            + factors["rag_match_quality"] * _WEIGHTS["rag_match_quality"]
            + factors["ml_prediction_score"] * _WEIGHTS["ml_prediction_score"]
            + factors["symptom_completeness"] * _WEIGHTS["symptom_completeness"]
        )
        penalty_total = (
            hallucination_penalty * _WEIGHTS["hallucination_penalty"]
            + contradiction_penalty * _WEIGHTS["contradiction_penalty"]
        )
        normalized = positive_score / 0.85
        final_score = max(0.0, min(1.0, normalized - penalty_total))
        reason = _generate_reason(final_score, uncertainty_flags)

        return ConfidenceReport(
            score=round(final_score, 3),
            reason=reason,
            factors={key: round(value, 3) for key, value in factors.items()},
            uncertainty_flags=uncertainty_flags,
        )
    except Exception as exc:
        logger.error("Confidence scoring failed: %s", exc, exc_info=True)
        return ConfidenceReport(
            score=0.5,
            reason="Confidence scoring unavailable. Moderate uncertainty assumed.",
            factors={},
            uncertainty_flags=["scoring_engine_error"],
        )


def _extract_max_ml_confidence(context: ConversationContext) -> float:
    scores: list[float] = []
    for value in context.ml_predictions.values():
        if isinstance(value, dict):
            scores.append(float(value.get("probability", 0.0) or 0.0))
        elif isinstance(value, (int, float)):
            scores.append(float(value))
    return max(scores, default=0.0)


def _generate_reason(score: float, flags: list[str]) -> str:
    if score >= 0.80:
        return "High confidence: strong evidence grounding, consistent signals, and a complete enough symptom picture."
    if score >= 0.55:
        reason = "Moderate confidence: some uncertainty remains"
        if flags:
            reason += f" because of {', '.join(flag.replace('_', ' ') for flag in flags[:2])}"
        return reason + "."
    if score >= 0.35:
        return "Low confidence: the available evidence is limited, so clinical verification is recommended."
    return "Very low confidence: there is not enough reliable data for a strong assessment. Please consult a healthcare professional."
