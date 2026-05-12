from __future__ import annotations

from typing import Any

from ai.safety.classifiers.emergency_classifier import EmergencyClassifier
from ai.safety.core.validator_engine import ValidatorEngine


class SafetyValidator:
    DEFAULT_DISCLAIMER = "This is supportive health information only and not a diagnosis."

    def __init__(self) -> None:
        self.engine = ValidatorEngine()
        self.emergency_classifier = EmergencyClassifier()

    def validate(self, context: dict[str, Any]) -> dict[str, Any]:
        query = str(context.get("query") or "").strip()
        symptoms = context.get("symptoms")
        symptom_text = ", ".join(str(item) for item in symptoms) if isinstance(symptoms, list) else str(symptoms or "")
        emergency = self.emergency_classifier.classify(query=query, text=symptom_text)
        recommendations = []
        if emergency.get("detected"):
            recommendations.append("Seek urgent in-person care now.")
        else:
            recommendations.append("Use cautious, educational guidance only.")
        return {
            "disclaimer": self.DEFAULT_DISCLAIMER,
            "confidence_floor": 0.2 if emergency.get("detected") else 0.4,
            "emergency_detected": bool(emergency.get("detected")),
            "requires_immediate_care": bool(emergency.get("detected")),
            "safety_notes": [self.emergency_classifier.escalation_message(str(emergency.get("tier") or "general"))]
            if emergency.get("detected")
            else [],
            "recommendations": recommendations,
        }

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

    async def validate_workflow_response(
        self,
        *,
        workflow: str,
        request: Any,
        context: Any,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        provider = (
            str(response.get("provider") or "").strip()
            or str(getattr(context, "provider_metadata", {}).get("provider") or "").strip()
            or "deterministic_fallback"
        )
        validation = self.engine.validate(
            payload=response,
            workflow=workflow,
            channel="workflow_engine",
            provider=provider,
            query=str(getattr(request, "query", "") or ""),
            conversation_history=getattr(request, "conversation_history", None),
            degraded_mode=bool(response.get("degraded") or response.get("fallback_used") or getattr(context, "fallback_activated", False)),
            fallback_used=bool(response.get("fallback_used") or getattr(context, "fallback_activated", False)),
        )
        return validation.as_dict()
