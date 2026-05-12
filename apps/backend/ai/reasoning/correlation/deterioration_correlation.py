from __future__ import annotations

from typing import Any

from ..schemas import NarrativeContext, ReasoningCard


class DeteriorationCorrelation:
    def analyze(
        self,
        context: NarrativeContext,
        *,
        temporal: dict[str, Any],
        causal_cards: list[ReasoningCard],
    ) -> dict[str, Any]:
        worsening = temporal.get("trend_state") == "deteriorating"
        cluster_count = len(causal_cards)
        severity = "high" if worsening and cluster_count >= 2 else "medium" if worsening or cluster_count else "low"
        summary = "No strong multi-signal deterioration cluster is present."
        if worsening and cluster_count:
            summary = "Several related signals are worsening together, which makes the deterioration pattern more credible than isolated metric noise."
        elif worsening:
            summary = "Temporal signals suggest deterioration, although the cross-metric cluster is still limited."
        return {
            "severity": severity,
            "summary": summary,
            "cluster_count": cluster_count,
        }
