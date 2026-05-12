from __future__ import annotations

from ..schemas import NarrativeContext


class NarrativeMemory:
    def build(self, context: NarrativeContext) -> dict[str, list[str] | str]:
        return {
            "last_persona": str(context.memory.get("last_persona") or ""),
            "report_summaries": [
                str(item.get("summary") or item.get("title"))
                for item in context.report_summaries[:3]
                if isinstance(item, dict) and (item.get("summary") or item.get("title"))
            ],
        }
