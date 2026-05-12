from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .safety_metadata import SafetyMetadata


@dataclass(slots=True)
class ValidationResult:
    original_payload: dict[str, Any] = field(default_factory=dict)
    sanitized_payload: dict[str, Any] = field(default_factory=dict)
    metadata: SafetyMetadata = field(default_factory=SafetyMetadata)
    safe: bool = True
    reason: str = ""

    @property
    def final_text(self) -> str:
        payload = self.sanitized_payload if isinstance(self.sanitized_payload, dict) else {}
        for key in (
            "message",
            "summary",
            "clinical_summary",
            "clinical_interpretation",
            "patient_summary",
            "analysis",
            "response",
        ):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def as_dict(self) -> dict[str, Any]:
        payload = dict(self.sanitized_payload)
        metadata = self.metadata.as_dict()
        payload["safety"] = metadata
        payload["severity"] = metadata["severity"]
        payload["escalation_level"] = metadata["escalation_level"]
        payload["emergency_detected"] = metadata["emergency_detected"]
        payload["emergency_flags"] = metadata["emergency_flags"]
        payload["clinician_escalation_recommended"] = metadata["clinician_escalation_recommended"]
        payload["safety_score"] = metadata["safety_score"]
        payload["hallucination_risk"] = metadata["hallucination_risk"]
        payload["disclaimer_applied"] = metadata["disclaimer_applied"]
        payload["response_modified"] = metadata["response_modified"]
        return payload
