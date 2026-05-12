from __future__ import annotations

import re
from typing import Any

from ..core.response_sanitizer import ResponseSanitizer


class ToneValidator:
    def __init__(self) -> None:
        self.sanitizer = ResponseSanitizer()

    def apply(self, payload: dict[str, Any], *, policy: dict[str, Any]) -> dict[str, Any]:
        updated = self.sanitizer.transform_payload(
            payload,
            policy=policy,
            text_transform=self._moderate_tone,
        )
        return {"payload": updated, "flags": ["tone_adjusted"] if updated != payload else [], "modified": updated != payload}

    def _moderate_tone(self, text: str, path: tuple[str, ...]) -> str:
        updated = text
        replacements = (
            (r"\bAs an AI language model[, ]*", ""),
            (r"\bthis is terrifying\b", "this can feel concerning"),
            (r"\byou should panic\b", "please seek prompt medical attention"),
            (r"\bcatastrophic\b", "serious"),
            (r"\bobviously\b", ""),
            (r"!{2,}", "."),
        )
        for pattern, replacement in replacements:
            updated = re.sub(pattern, replacement, updated, flags=re.IGNORECASE)
        updated = re.sub(r"\s{2,}", " ", updated).strip()
        words = updated.split()
        if len(words) > 120 and path and path[-1] != "full_analysis":
            updated = " ".join(words[:120]).rstrip(" ,;") + "."
        return updated
