from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class SafetyMetadata:
    workflow: str = "generic"
    channel: str = "unknown"
    provider: str = "unknown"
    severity: str = "low"
    escalation_level: str = "none"
    safety_score: float = 1.0
    hallucination_risk: float = 0.0
    emergency_detected: bool = False
    disclaimer_applied: list[str] = field(default_factory=list)
    response_modified: bool = False
    clinician_escalation_recommended: bool = False
    validation_flags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    emergency_flags: list[str] = field(default_factory=list)
    blocked_categories: list[str] = field(default_factory=list)
    provider_risk: str = "standard"
    degraded_mode: bool = False
    failure_safe_triggered: bool = False
    validator_version: str = "ai-safety-v2"

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["safety_score"] = round(float(self.safety_score or 0.0), 4)
        payload["hallucination_risk"] = round(float(self.hallucination_risk or 0.0), 4)
        return payload
