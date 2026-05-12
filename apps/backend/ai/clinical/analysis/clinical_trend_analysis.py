from __future__ import annotations

from typing import Any

from ..utils import classify_trend, dedupe_texts, safe_list, safe_text, structured_log


class ClinicalTrendAnalysis:
    @staticmethod
    def analyze(context: dict[str, Any]) -> dict[str, Any]:
        vitals = context.get("vitals") if isinstance(context.get("vitals"), dict) else {}
        history = vitals.get("history") if isinstance(vitals.get("history"), dict) else {}
        metrics = []
        for metric_name, points in history.items():
            metrics.append(classify_trend(metric_name, points))
        metrics.sort(
            key=lambda item: (
                0 if item.get("state") == "deteriorating" else 1 if item.get("state") == "improving" else 2,
                -int(item.get("point_count") or 0),
            )
        )

        deteriorating = [item for item in metrics if item.get("state") == "deteriorating"]
        improving = [item for item in metrics if item.get("state") == "improving"]
        stable = [item for item in metrics if item.get("state") == "stable"]
        if deteriorating:
            overall_state = "deteriorating"
            headline = f"Recent longitudinal monitoring shows deterioration in {', '.join(item['label'] for item in deteriorating[:2])}."
        elif improving:
            overall_state = "improving"
            headline = f"Recent longitudinal monitoring shows recovery in {', '.join(item['label'] for item in improving[:2])}."
        elif stable:
            overall_state = "stable"
            headline = "Recent longitudinal monitoring is largely stable."
        else:
            overall_state = "insufficient_data"
            headline = "There is limited longitudinal monitoring data available."

        summary_points = dedupe_texts([item.get("narrative") for item in metrics], limit=4)
        domains = dedupe_texts([item.get("domain") for item in deteriorating], limit=4)
        structured_log(
            "[CLINICAL_SUMMARY]",
            patient_id=safe_text(context.get("patient", {}).get("id")),
            trend_state=overall_state,
            deteriorating=len(deteriorating),
            improving=len(improving),
        )
        return {
            "overall_state": overall_state,
            "headline": headline,
            "metric_trends": metrics,
            "deteriorating_metrics": deteriorating,
            "improving_metrics": improving,
            "stable_metrics": stable,
            "dominant_domains": domains,
            "recent_change_summary": summary_points,
            "signals_reviewed": len(metrics),
            "key_changes": [
                {
                    "metric": item.get("metric"),
                    "label": item.get("label"),
                    "state": item.get("state"),
                    "delta": item.get("delta"),
                    "narrative": item.get("narrative"),
                }
                for item in metrics[:5]
            ],
            "evidence_ids": dedupe_texts(
                [
                    safe_text(item.get("latest_timestamp"))
                    for item in safe_list(metrics)
                ],
                limit=5,
            ),
        }
