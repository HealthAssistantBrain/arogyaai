from __future__ import annotations

import re
from typing import Any

from ..models.payloads import ProviderRequest, ProviderResponse


class MedicalSafetyValidator:
    disclaimer = "This guidance is supportive only and does not replace urgent or in-person medical care."
    risky_patterns = (
        r"\bdefinitely\b",
        r"\bguaranteed\b",
        r"\bcure\b",
        r"\bno need to see a doctor\b",
    )

    def validate(self, response: ProviderResponse, request: ProviderRequest) -> ProviderResponse:
        content = dict(response.content)
        warnings = list(response.warnings)

        for field in ("summary", "message", "clinical_summary", "clinical_interpretation", "understanding"):
            value = str(content.get(field) or "").strip()
            if not value:
                continue
            sanitized = value
            for pattern in self.risky_patterns:
                if re.search(pattern, sanitized, flags=re.IGNORECASE):
                    warnings.append(f"unsafe_phrase_removed:{field}")
                    sanitized = re.sub(pattern, "may", sanitized, flags=re.IGNORECASE)
            content[field] = sanitized.strip()

        confidence = float(content.get("confidence_score") or response.confidence or 0.0)
        if confidence > 0.95:
            warnings.append("confidence_capped")
            confidence = 0.95
        content["confidence_score"] = round(max(0.0, min(1.0, confidence)), 4)

        disclaimers = []
        for value in (content.get("disclaimer"), content.get("medical_disclaimer")):
            text = str(value or "").strip()
            if text:
                disclaimers.append(text)
        if self.disclaimer not in disclaimers:
            disclaimers.append(self.disclaimer)
        content["disclaimer"] = disclaimers[0]
        content["medical_disclaimer"] = disclaimers[0]
        content.setdefault("safe", True)
        content.setdefault("workflow", request.workflow)
        content.setdefault("task", request.task)

        response.content = content
        response.confidence = content["confidence_score"]
        response.warnings = warnings
        response.safe = True
        return response
