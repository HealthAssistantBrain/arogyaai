from __future__ import annotations

import re


class VerbosityController:
    REPETITIONS = (
        "based on your recent data",
        "based on your data",
        "it is important to note",
        "please note that",
    )

    def trim(self, text: str, *, target_words: int) -> str:
        normalized = str(text or "").strip()
        for phrase in self.REPETITIONS:
            normalized = re.sub(re.escape(phrase), "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s{2,}", " ", normalized).strip()
        words = normalized.split()
        if len(words) <= target_words:
            return normalized
        trimmed = " ".join(words[:target_words]).rstrip(",;:")
        if trimmed and trimmed[-1] not in ".!?":
            trimmed += "."
        return trimmed

    def reduce_repetition(self, values: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value or "").strip()
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            deduped.append(text)
        return deduped
