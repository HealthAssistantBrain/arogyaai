from __future__ import annotations

from ..schemas import NarrativeContext, ReasoningCard


class AnomalyReasoner:
    def analyze(self, context: NarrativeContext) -> list[ReasoningCard]:
        if not context.anomalies:
            return []
        primary = context.anomalies[0]
        return [
            ReasoningCard(
                kind="anomaly",
                domain="anomaly",
                title=primary.get("title") or "Anomaly cluster detected",
                summary=primary.get("summary") or "Several signals moved outside your usual pattern.",
                severity=primary.get("severity") or "medium",
                confidence=0.74,
                timeframe="7d",
                evidence=[item.get("summary") or item.get("title") for item in context.anomalies[:3] if item.get("summary") or item.get("title")],
                metrics=[item.get("metric") for item in context.anomalies[:4] if item.get("metric")],
                recommendations=["Focus on whether the same cluster repeats instead of over-weighting a single isolated anomaly."],
                tags=["anomaly_cluster"],
            )
        ]
