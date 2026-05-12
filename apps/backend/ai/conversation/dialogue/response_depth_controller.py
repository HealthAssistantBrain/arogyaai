from __future__ import annotations

from ..schemas import DialogueContext, MemorySnapshot


class ResponseDepthController:
    DEFAULT_WORD_LIMITS = {
        "micro": 22,
        "short": 70,
        "medium": 135,
        "detailed": 210,
        "expert": 320,
    }

    def resolve(self, context: DialogueContext, snapshot: MemorySnapshot) -> dict[str, int | str]:
        depth = context.depth or "short"
        base_limit = self.DEFAULT_WORD_LIMITS.get(depth, 90)
        complexity_bonus = 0
        if context.word_count() >= 18:
            complexity_bonus += 18
        if len(snapshot.symptom.active_symptoms) >= 2:
            complexity_bonus += 10
        if snapshot.symptom.trend_signals:
            complexity_bonus += 14
        if context.mode == "expert":
            complexity_bonus += 36
        if context.risk_level.lower() in {"high", "critical", "emergency"}:
            complexity_bonus -= 12
        target_words = max(18, base_limit + complexity_bonus)
        chunk_target = 16 if depth in {"micro", "short"} else 22 if depth == "medium" else 30
        return {
            "depth": depth,
            "target_words": target_words,
            "chunk_target_words": chunk_target,
            "paragraph_limit": 1 if depth == "micro" else 2 if depth in {"short", "medium"} else 3,
        }
