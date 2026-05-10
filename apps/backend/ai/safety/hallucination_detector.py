from __future__ import annotations

import logging
import re

from .clinical_rules import HIGH_RISK_TERMS, RAG_MIN_CONFIDENCE_THRESHOLD
from .safety_types import ConversationContext, HallucinationReport

logger = logging.getLogger("arogyaai.safety.hallucination")

_CLAIM_PATTERNS = [
    re.compile(r"you (?:may|might|could|appear to) (?:have|be experiencing|show signs of)\s+([a-zA-Z\s\-]+)", re.IGNORECASE),
    re.compile(r"this (?:suggests?|indicates?|may indicate)\s+([a-zA-Z\s\-]+)", re.IGNORECASE),
    re.compile(r"(?:associated with|consistent with|related to)\s+([a-zA-Z\s\-]+)", re.IGNORECASE),
    re.compile(r"(?:risk|likelihood) of\s+([a-zA-Z\s\-]+)", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d+)?)\s*%\s+(?:chance|risk|probability|likelihood)", re.IGNORECASE),
]

_STAT_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*%\s+(?:chance|risk|probability|likelihood|of patients?)\b",
    re.IGNORECASE,
)

_HIGH_RISK_PATTERN = re.compile("|".join(re.escape(term) for term in HIGH_RISK_TERMS), re.IGNORECASE)


def detect_hallucinations(ai_response: str, context: ConversationContext) -> HallucinationReport:
    try:
        claims = _extract_claims(ai_response)
        fabricated_stats = _extract_fabricated_stats(ai_response, context)
        unsupported = _find_unsupported_claims(claims, context)
        rag_coverage = _compute_rag_coverage(context)
        severity = _compute_severity(unsupported, fabricated_stats, rag_coverage)
        return HallucinationReport(
            detected=severity != "none",
            fabricated_claims=fabricated_stats,
            unsupported_phrases=unsupported,
            rag_coverage=rag_coverage,
            severity=severity,
        )
    except Exception as exc:
        logger.error("Hallucination detector failed: %s", exc, exc_info=True)
        return HallucinationReport(
            detected=False,
            fabricated_claims=[],
            unsupported_phrases=[],
            rag_coverage=0.5,
            severity="mild",
        )


def _extract_claims(text: str) -> list[str]:
    claims: list[str] = []
    for pattern in _CLAIM_PATTERNS:
        for match in pattern.finditer(text or ""):
            claim_text = (match.group(1) if match.lastindex else match.group(0) or "").strip()
            if len(claim_text) > 3:
                claims.append(claim_text.lower())
    return list(dict.fromkeys(claims))


def _extract_fabricated_stats(text: str, context: ConversationContext) -> list[str]:
    fabricated: list[str] = []
    for match in _STAT_PATTERN.finditer(text or ""):
        stat_text = match.group(0)
        grounded = any(stat_text.lower() in str(doc.get("content") or "").lower() for doc in context.rag_evidence)
        if not grounded:
            fabricated.append(stat_text)
    return fabricated


def _find_unsupported_claims(claims: list[str], context: ConversationContext) -> list[str]:
    unsupported: list[str] = []
    ml_labels = _get_ml_labels(context.ml_predictions)
    rag_texts = [str(doc.get("content") or "").lower() for doc in context.rag_evidence]
    user_symptoms = [symptom.lower() for symptom in context.user_symptoms]

    for claim in claims:
        touches_high_risk = bool(_HIGH_RISK_PATTERN.search(claim))
        in_rag = any(_keyword_overlap(claim, rag_text) >= 0.4 for rag_text in rag_texts)
        in_ml = any(label in claim for label in ml_labels)
        in_symptoms = any(symptom in claim for symptom in user_symptoms)
        grounded = in_rag or in_ml or in_symptoms
        if touches_high_risk and not grounded:
            unsupported.append(claim)
        elif not grounded and len(claim) > 8:
            unsupported.append(claim)

    return unsupported


def _get_ml_labels(ml_predictions: dict[str, object]) -> list[str]:
    labels: list[str] = []
    for disease, value in ml_predictions.items():
        if isinstance(value, dict):
            if float(value.get("probability", 0) or 0) > 0.35:
                labels.append(disease.lower().replace("_", " "))
        elif isinstance(value, (int, float)) and float(value) > 0.35:
            labels.append(disease.lower().replace("_", " "))
    return labels


def _compute_rag_coverage(context: ConversationContext) -> float:
    if not context.rag_evidence:
        return 0.0
    return max(0.0, min(1.0, float(context.rag_confidence or 0.0)))


def _keyword_overlap(claim: str, reference: str) -> float:
    claim_words = set(claim.lower().split())
    reference_words = set(reference.lower().split())
    if not claim_words:
        return 0.0
    return len(claim_words & reference_words) / len(claim_words)


def _compute_severity(unsupported: list[str], fabricated: list[str], rag_coverage: float) -> str:
    if fabricated:
        return "severe"
    count = len(unsupported)
    if count == 0 and rag_coverage >= RAG_MIN_CONFIDENCE_THRESHOLD:
        return "none"
    if count == 0:
        return "mild"
    if count == 1 and rag_coverage >= RAG_MIN_CONFIDENCE_THRESHOLD:
        return "mild"
    if count <= 2 or rag_coverage < RAG_MIN_CONFIDENCE_THRESHOLD:
        return "moderate"
    return "severe"
