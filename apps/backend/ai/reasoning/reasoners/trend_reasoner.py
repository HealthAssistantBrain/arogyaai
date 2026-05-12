from __future__ import annotations

from ..schemas import NarrativeContext, ReasoningCard


class TrendReasoner:
    def analyze(self, context: NarrativeContext) -> list[ReasoningCard]:
        summaries = context.memory.get("major_trends") or []
        if not summaries:
            return []
        return [
            ReasoningCard(
                kind="trend",
                domain="trend",
                title="Longitudinal trend context",
                summary=str(summaries[0]),
                severity="medium",
                confidence=0.63,
                timeframe="long_term",
                evidence=[str(item) for item in summaries[:3]],
                metrics=[],
                recommendations=[],
                tags=["longitudinal"],
            )
        ]
