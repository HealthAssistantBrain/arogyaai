from __future__ import annotations

from typing import Any

from services.agents.safety_agent import SafetyGuardAgent


class SafetyValidator:
    DEFAULT_DISCLAIMER = "This guidance is supportive only and does not replace urgent or in-person medical care."

    def validate(self, context: dict[str, Any]) -> dict[str, Any]:
        payload = SafetyGuardAgent().run(context)
        payload["disclaimer"] = self.DEFAULT_DISCLAIMER
        payload["confidence_floor"] = 0.2 if payload.get("requires_immediate_care") else 0.4
        payload["emergency_detected"] = bool(payload.get("requires_immediate_care"))
        return payload

    def apply(self, response: dict[str, Any], safety: dict[str, Any]) -> dict[str, Any]:
        merged = dict(response or {})
        safety_notes = merged.get("safety_notes") if isinstance(merged.get("safety_notes"), list) else []
        extra_notes = safety.get("safety_notes") if isinstance(safety.get("safety_notes"), list) else []
        merged["safety_notes"] = [item for item in [*safety_notes, *extra_notes] if item]
        if merged["safety_notes"]:
            merged["safety_note"] = merged["safety_notes"][0]
        merged["disclaimer"] = safety.get("disclaimer") or self.DEFAULT_DISCLAIMER
        merged["emergency_detected"] = bool(safety.get("emergency_detected"))
        merged["safety"] = safety
        return merged
