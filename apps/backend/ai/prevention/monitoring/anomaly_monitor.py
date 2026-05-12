from __future__ import annotations

from ..utils import anomaly_count, anomaly_weight, clamp, current_overall_risk, safe_dict, safe_list, safe_text
from .common import build_signal


class AnomalyMonitor:
    DOMAIN = "anomaly"

    @staticmethod
    def evaluate(context: dict) -> dict:
        anomalies = safe_list(context.get("current_anomalies"))
        risk = anomaly_weight(context) + current_overall_risk(context) * 0.25
        recurrence_tags = []
        if anomalies:
            recurrence_tags = [
                safe_text(safe_dict(item).get("domain") or safe_dict(item).get("metric") or "general")
                for item in anomalies[:4]
            ]
        summary = (
            "Recent anomalies are recurring often enough to justify a stronger preventive response."
            if risk >= 55.0
            else "Recent anomalies look limited, but they should still be rechecked if they recur."
        )
        signal = build_signal(
            domain=AnomalyMonitor.DOMAIN,
            kind="recurrence",
            summary=summary,
            risk_score=clamp(risk),
            confidence=0.74 if anomalies else 0.55,
            direction="worsening" if anomalies else "stable",
            value=float(anomaly_count(context)),
            baseline_delta=None,
            persistence_days=float(min(7, len(anomalies))),
            acceleration=0.12 * max(1, len(anomalies)),
            monitor="anomaly_monitor",
            supporting_metrics={
                "anomaly_count": len(anomalies),
                "anomaly_domains": recurrence_tags,
            },
            recommended_actions=[
                "Recheck the abnormal signal instead of assuming it will self-resolve.",
                "Escalate the pattern sooner if anomalies repeat across multiple domains.",
            ],
            tags=["anomaly_escalation", *recurrence_tags],
        )
        return signal.model_dump(mode="json")
