from __future__ import annotations

import re
from typing import Any

from ..core.response_sanitizer import ResponseSanitizer


class DiagnosisGuard:
    def __init__(self) -> None:
        self.sanitizer = ResponseSanitizer()

    def apply(self, payload: dict[str, Any], *, policy: dict[str, Any]) -> dict[str, Any]:
        updated = self.sanitizer.transform_payload(
            payload,
            policy=policy,
            text_transform=self._soften_diagnosis_language,
        )
        flags: list[str] = []
        if updated != payload:
            flags.append("diagnosis_softened")
        return {"payload": updated, "flags": flags, "modified": updated != payload}

    def _soften_diagnosis_language(self, text: str, path: tuple[str, ...]) -> str:
        updated = text
        replacements = (
            (r"\bdiagnosed with\b", "worth evaluating for"),
            (r"\byour diagnosis is\b", "one possibility to discuss with a clinician is"),
            (r"\bnot a serious issue\b", "not possible to confirm as serious or not from this alone"),
        )
        for pattern, replacement in replacements:
            updated = re.sub(pattern, replacement, updated, flags=re.IGNORECASE)
        return updated
