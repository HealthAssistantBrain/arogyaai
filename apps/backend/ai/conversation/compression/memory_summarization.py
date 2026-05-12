from __future__ import annotations

from ..schemas import MemorySnapshot


class MemorySummarization:
    def summarize(self, snapshot: MemorySnapshot) -> str:
        clauses: list[str] = []
        if snapshot.conversational.continuity_reference:
            clauses.append(snapshot.conversational.continuity_reference)
        if snapshot.symptom.active_symptoms:
            clauses.append("Active symptoms: " + ", ".join(snapshot.symptom.active_symptoms[:3]))
        if snapshot.symptom.trend_signals:
            clauses.append(snapshot.symptom.trend_signals[0])
        if snapshot.conversational.prior_recommendations:
            clauses.append("Prior plan: " + snapshot.conversational.prior_recommendations[0])
        if snapshot.topic.active_topics:
            clauses.append("Topics in play: " + ", ".join(snapshot.topic.active_topics[:3]))
        if not clauses and snapshot.narrative.longitudinal_summary:
            clauses.append(snapshot.narrative.longitudinal_summary)
        return " | ".join(clauses[:4])
