from __future__ import annotations

import re


class ConversationalPacing:
    LABELS = {
        "micro": "Arya is typing...",
        "short": "Arya is typing...",
        "medium": "Thinking this through...",
        "detailed": "Working through your context...",
        "expert": "Analyzing your data...",
    }

    def build(self, message: str, *, depth: str, target_chunk_words: int = 22) -> dict[str, object]:
        normalized = str(message or "").strip()
        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", normalized) if item.strip()]
        if not sentences:
            return {
                "chunks": [],
                "typing_label": self.LABELS.get(depth, self.LABELS["short"]),
                "chunk_strategy": "sentence",
                "typing_delay_ms": 90,
            }

        chunks: list[str] = []
        current: list[str] = []
        current_words = 0
        for sentence in sentences:
            words = len(sentence.split())
            if current and current_words + words > target_chunk_words:
                chunks.append(" ".join(current).strip())
                current = []
                current_words = 0
            current.append(sentence)
            current_words += words
        if current:
            chunks.append(" ".join(current).strip())

        depth_delay = {"micro": 50, "short": 65, "medium": 80, "detailed": 95, "expert": 110}
        return {
            "chunks": chunks,
            "typing_label": self.LABELS.get(depth, self.LABELS["short"]),
            "chunk_strategy": "sentence",
            "typing_delay_ms": depth_delay.get(depth, 80),
        }
