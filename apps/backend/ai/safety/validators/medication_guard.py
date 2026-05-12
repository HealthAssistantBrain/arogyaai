from __future__ import annotations

import re
from typing import Any

from ..core.response_sanitizer import ResponseSanitizer

_DOSAGE_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|units?)\b",
    re.IGNORECASE,
)
_MEDICATION_ACTION_PATTERN = re.compile(
    r"\b(?:take|start|stop|use|prescribe|begin|increase|decrease)\b.{0,80}\b(?:tablet|capsule|mg|ml|metformin|ibuprofen|lisinopril|paracetamol|acetaminophen|insulin)\b",
    re.IGNORECASE,
)


class MedicationGuard:
    def __init__(self) -> None:
        self.sanitizer = ResponseSanitizer()

    def apply(self, payload: dict[str, Any], *, policy: dict[str, Any]) -> dict[str, Any]:
        corpus = self.sanitizer.collect_text(payload, policy=policy)
        blocked = bool(_DOSAGE_PATTERN.search(corpus) or _MEDICATION_ACTION_PATTERN.search(corpus))
        if not blocked:
            return {"payload": payload, "flags": [], "modified": False, "blocked": False}

        updated = self.sanitizer.transform_payload(
            payload,
            policy=policy,
            text_transform=self._remove_medication_directives,
        )
        recommendations = updated.get("recommendations") if isinstance(updated.get("recommendations"), list) else []
        educational = "For medication decisions, dosing, or starting/stopping treatment, please speak with a clinician or pharmacist."
        if educational not in recommendations:
            updated["recommendations"] = [*recommendations[:3], educational]
        return {
            "payload": updated,
            "flags": ["unsafe_medication_advice"],
            "modified": True,
            "blocked": True,
        }

    def _remove_medication_directives(self, text: str, path: tuple[str, ...]) -> str:
        updated = _DOSAGE_PATTERN.sub("specific dosing", text)
        updated = _MEDICATION_ACTION_PATTERN.sub(
            "Please discuss medication choice and dosing with a licensed clinician or pharmacist",
            updated,
        )
        return updated
