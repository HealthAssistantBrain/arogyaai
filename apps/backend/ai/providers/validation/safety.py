from __future__ import annotations

from typing import Any

from ...safety.core.validator_engine import ValidatorEngine
from ..models.payloads import ProviderRequest, ProviderResponse


class MedicalSafetyValidator:
    def __init__(self) -> None:
        self.engine = ValidatorEngine()

    def validate(self, response: ProviderResponse, request: ProviderRequest) -> ProviderResponse:
        validation = self.engine.validate(
            payload=response.content,
            workflow=request.workflow,
            channel="provider_runtime",
            provider=response.provider,
            query=str(request.context.get("query") or request.metadata.get("query") or ""),
            conversation_history=request.conversation_history,
            degraded_mode=bool(response.degraded),
            fallback_used=bool(response.fallback_used),
        )
        content = validation.as_dict()
        content.setdefault("workflow", request.workflow)
        content.setdefault("task", request.task)
        capped_confidence = min(
            float(content.get("confidence_score") or response.confidence or 0.0),
            float(0.58 if validation.metadata.provider_risk == "maximum" else 0.82 if validation.metadata.provider_risk == "strict" else 0.9),
        )
        content["confidence_score"] = round(max(0.0, min(1.0, capped_confidence)), 4)
        response.content = content
        response.text = validation.final_text or response.text
        response.confidence = content["confidence_score"]
        response.safe = validation.safe
        response.warnings = list(dict.fromkeys([*response.warnings, *validation.metadata.validation_flags, *validation.metadata.warnings]))
        response.metadata["safety"] = validation.metadata.as_dict()
        return response
