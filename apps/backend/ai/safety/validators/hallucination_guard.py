from __future__ import annotations

import re
from typing import Any

from ..core.response_sanitizer import ResponseSanitizer

_CERTAINTY_PATTERNS = (
    r"\byou definitely have\b",
    r"\byou have\b",
    r"\bthis confirms\b",
    r"\bdefinitive(?:ly)?\b",
    r"\bguaranteed\b",
    r"\bcertainly\b",
    r"\bno doubt\b",
    r"\bwithout question\b",
)
_FAKE_REFERENCE_PATTERNS = (
    r"\baccording to (?:the )?(?:who|cdc|nih)\b",
    r"\bstudies prove\b",
    r"\bresearch proves\b",
)
_STAT_PATTERN = re.compile(r"\b\d+(?:\.\d+)?%")


class HallucinationGuard:
    def __init__(self) -> None:
        self.sanitizer = ResponseSanitizer()

    def apply(self, payload: dict[str, Any], *, policy: dict[str, Any]) -> dict[str, Any]:
        flags: list[str] = []
        risk = 0.0
        corpus = self.sanitizer.collect_text(payload, policy=policy)
        lowered = corpus.lower()

        certainty_hits = sum(1 for pattern in _CERTAINTY_PATTERNS if re.search(pattern, lowered, flags=re.IGNORECASE))
        if certainty_hits:
            flags.append("fake_certainty")
            risk += min(0.45, certainty_hits * 0.14)

        if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in _FAKE_REFERENCE_PATTERNS):
            flags.append("fake_reference")
            risk += 0.25

        if _STAT_PATTERN.search(corpus) and not payload.get("citations") and not payload.get("sources"):
            flags.append("fabricated_statistics")
            risk += 0.28

        updated = self.sanitizer.transform_payload(
            payload,
            policy=policy,
            text_transform=self._soften_text,
        )
        if policy.get("is_ocr"):
            updated = self.sanitizer.transform_payload(
                updated,
                policy=policy,
                text_transform=self._ocr_softening,
            )
        return {
            "payload": updated,
            "flags": flags,
            "hallucination_risk": round(min(1.0, risk), 4),
            "modified": updated != payload,
        }

    def _soften_text(self, text: str, path: tuple[str, ...]) -> str:
        updated = text
        replacements = (
            (r"\byou definitely have ([A-Za-z][A-Za-z \-/]{2,60})\b", r"This may align with several conditions, including \1"),
            (r"\byou have ([A-Za-z][A-Za-z \-/]{2,60})\b", r"This may be consistent with \1"),
            (r"\bthis confirms ([A-Za-z][A-Za-z \-/]{2,60})\b", r"This may suggest \1"),
            (r"\bdefinitely\b", "may"),
            (r"\bguaranteed\b", "not certain"),
            (r"\bcertainly\b", "possibly"),
            (r"\bno doubt\b", "with limited certainty"),
            (r"\bwithout question\b", "based on limited information"),
        )
        for pattern, replacement in replacements:
            updated = re.sub(pattern, replacement, updated, flags=re.IGNORECASE)
        return updated

    def _ocr_softening(self, text: str, path: tuple[str, ...]) -> str:
        updated = re.sub(r"\bthis means you have\b", "These extracted findings may be consistent with", text, flags=re.IGNORECASE)
        updated = re.sub(r"\bthe report proves\b", "The report may suggest", updated, flags=re.IGNORECASE)
        updated = re.sub(r"\bdiagnosis\b", "clinical interpretation", updated, flags=re.IGNORECASE)
        return updated
