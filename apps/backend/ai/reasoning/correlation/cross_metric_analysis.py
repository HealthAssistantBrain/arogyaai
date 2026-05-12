from __future__ import annotations

from typing import Any

from ..schemas import NarrativeContext, ReasoningCard


class CrossMetricAnalysis:
    def analyze(
        self,
        context: NarrativeContext,
        *,
        correlations: list[ReasoningCard],
        physiological_cards: list[ReasoningCard],
    ) -> dict[str, Any]:
        fatigue_cluster = next((card for card in physiological_cards if card.domain == "fatigue"), None)
        cluster_summary = fatigue_cluster.summary if fatigue_cluster else ""
        if not cluster_summary and correlations:
            cluster_summary = correlations[0].summary
        return {
            "clusters": [
                {
                    "title": fatigue_cluster.title if fatigue_cluster else "Cross-metric signal cluster",
                    "summary": cluster_summary,
                    "domains": [card.domain for card in correlations[:4]],
                }
            ]
            if cluster_summary
            else [],
            "combined_signal_count": len(correlations) + len([card for card in physiological_cards if card.kind == "cluster"]),
        }
