from __future__ import annotations

import re

from ..schemas import DialogueContext


class ClinicianStyleEngine:
    def polish(self, context: DialogueContext, paragraphs: list[str]) -> str:
        cleaned: list[str] = []
        seen: set[str] = set()
        for paragraph in paragraphs:
            text = re.sub(r"\s+", " ", str(paragraph or "")).strip()
            if not text:
                continue
            if text[-1] not in ".!?":
                text += "."
            text = text[0].upper() + text[1:]
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(text)
        if context.mode == "expert":
            return "\n\n".join(cleaned[:3])
        return "\n\n".join(cleaned[:2])
