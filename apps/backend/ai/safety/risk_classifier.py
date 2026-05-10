from __future__ import annotations

from .safety_types import ConfidenceReport, ContradictionReport, ConversationContext, EmergencyReport, HallucinationReport, RiskLevel


def classify_risk(
    emergency: EmergencyReport,
    hallucination: HallucinationReport,
    contradiction: ContradictionReport,
    confidence: ConfidenceReport,
    context: ConversationContext,
) -> RiskLevel:
    if emergency.is_emergency:
        return RiskLevel.EMERGENCY
    if contradiction.severity == "critical":
        return RiskLevel.URGENT
    if hallucination.severity == "severe":
        return RiskLevel.URGENT

    max_ml = _max_ml_probability(context.ml_predictions)
    if max_ml >= 0.75:
        return RiskLevel.URGENT

    if (
        hallucination.severity == "moderate"
        or contradiction.severity == "major"
        or max_ml >= 0.55
        or confidence.score < 0.40
    ):
        return RiskLevel.ELEVATED

    if (
        hallucination.severity == "mild"
        or contradiction.severity == "minor"
        or confidence.score < 0.60
        or not context.rag_evidence
    ):
        return RiskLevel.CAUTION

    return RiskLevel.SAFE


def get_tone_mode(risk_level: RiskLevel) -> str:
    return {
        RiskLevel.SAFE: "friendly_educational",
        RiskLevel.CAUTION: "careful_attentive",
        RiskLevel.ELEVATED: "careful_attentive",
        RiskLevel.URGENT: "direct_actionable",
        RiskLevel.EMERGENCY: "concise_escalation",
    }[risk_level]


def _max_ml_probability(ml_predictions: dict[str, object]) -> float:
    scores: list[float] = []
    for value in ml_predictions.values():
        if isinstance(value, dict):
            scores.append(float(value.get("probability", 0) or 0))
        elif isinstance(value, (int, float)):
            scores.append(float(value))
    return max(scores, default=0.0)
