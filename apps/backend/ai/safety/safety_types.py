from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    SAFE = "safe"
    CAUTION = "caution"
    ELEVATED = "elevated"
    URGENT = "urgent"
    EMERGENCY = "emergency"


class ValidationFlag(str, Enum):
    HALLUCINATION_DETECTED = "hallucination_detected"
    FAKE_CERTAINTY = "fake_certainty"
    UNSAFE_MEDICATION_ADVICE = "unsafe_medication_advice"
    EMERGENCY_CONDITION = "emergency_condition"
    CONTRADICTION_DETECTED = "contradiction_detected"
    LOW_RAG_GROUNDING = "low_rag_grounding"
    UNSUPPORTED_DIAGNOSIS = "unsupported_diagnosis"
    FORBIDDEN_PHRASE = "forbidden_phrase"
    OVERDOSE_RISK = "overdose_risk"
    MISSING_ESCALATION = "missing_escalation"


class ProviderType(str, Enum):
    NVIDIA = "nvidia"
    OLLAMA = "ollama"
    OPENAI = "openai"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ConversationContext:
    user_id: str
    session_id: str
    user_symptoms: list[str] = field(default_factory=list)
    vitals: dict[str, Any] = field(default_factory=dict)
    ml_predictions: dict[str, Any] = field(default_factory=dict)
    rag_evidence: list[dict[str, Any]] = field(default_factory=list)
    rag_confidence: float = 0.0
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    provider: ProviderType = ProviderType.UNKNOWN
    raw_model_confidence: float | None = None


@dataclass(slots=True)
class ValidationResult:
    original_response: str
    final_response: str
    risk_level: RiskLevel
    flags: list[ValidationFlag] = field(default_factory=list)
    confidence_score: float = 1.0
    confidence_reason: str = ""
    uncertainty_flags: list[str] = field(default_factory=list)
    rewritten: bool = False
    escalation_required: bool = False
    escalation_message: str | None = None
    processing_time_ms: float = 0.0
    pipeline_stages: list[str] = field(default_factory=list)

    def to_api_payload(self) -> dict[str, Any]:
        return {
            "response": self.final_response,
            "safety": {
                "risk_level": self.risk_level.value,
                "confidence_score": round(float(self.confidence_score or 0.0), 3),
                "confidence_reason": self.confidence_reason,
                "flags": [flag.value for flag in self.flags],
                "uncertainty_flags": list(self.uncertainty_flags),
                "escalation_required": self.escalation_required,
                "escalation_message": self.escalation_message,
                "rewritten": self.rewritten,
                "processing_time_ms": round(float(self.processing_time_ms or 0.0), 2),
                "pipeline_stages": list(self.pipeline_stages),
            },
        }


@dataclass(slots=True)
class HallucinationReport:
    detected: bool
    fabricated_claims: list[str]
    unsupported_phrases: list[str]
    rag_coverage: float
    severity: str


@dataclass(slots=True)
class EmergencyReport:
    is_emergency: bool
    matched_patterns: list[str]
    tier: str
    override_response: str | None = None


@dataclass(slots=True)
class ContradictionReport:
    detected: bool
    contradictions: list[dict[str, Any]]
    severity: str


@dataclass(slots=True)
class ConfidenceReport:
    score: float
    reason: str
    factors: dict[str, float]
    uncertainty_flags: list[str]
