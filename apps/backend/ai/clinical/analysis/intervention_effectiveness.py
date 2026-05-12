from __future__ import annotations

from typing import Any

from ..utils import dedupe_texts, safe_list, safe_text


def _match_metric_from_text(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("sleep", "recovery", "rest")):
        return "sleep"
    if any(token in lowered for token in ("activity", "steps", "exercise", "walk")):
        return "activity"
    if any(token in lowered for token in ("pressure", "heart", "cardio", "pulse")):
        return "heart_rate"
    return "general"


class InterventionEffectivenessAnalyzer:
    @staticmethod
    def analyze(context: dict[str, Any], trend_analysis: dict[str, Any]) -> dict[str, Any]:
        recommendations = safe_list(context.get("recommendations"))
        metric_index = {item.get("metric"): item for item in trend_analysis.get("metric_trends") or []}
        outcomes = []
        for raw in recommendations[:6]:
            if isinstance(raw, str):
                title = raw
                category = _match_metric_from_text(raw)
            elif isinstance(raw, dict):
                title = safe_text(raw.get("title") or raw.get("description") or raw.get("detail"))
                category = safe_text(raw.get("category")) or _match_metric_from_text(title)
            else:
                continue
            metric_key = _match_metric_from_text(f"{title} {category}")
            metric = metric_index.get(metric_key)
            if metric is None:
                status = "limited_data"
                score = 45.0
                narrative = "There is not enough post-intervention telemetry to judge clinical response yet."
            else:
                state = metric.get("state")
                if state == "improving":
                    status = "improving"
                    score = 78.0
                    narrative = f"Associated telemetry suggests the targeted domain is improving: {metric.get('narrative')}"
                elif state == "stable":
                    status = "partial_response"
                    score = 58.0
                    narrative = f"The targeted domain has stabilized but has not clearly recovered yet: {metric.get('narrative')}"
                else:
                    status = "not_stabilized"
                    score = 32.0
                    narrative = f"The targeted domain remains unstable despite intervention tracking: {metric.get('narrative')}"
            outcomes.append(
                {
                    "title": title,
                    "category": category or metric_key,
                    "status": status,
                    "effectiveness_score": score,
                    "narrative": narrative,
                    "evidence_ids": [safe_text(metric.get("latest_timestamp"))] if isinstance(metric, dict) and metric.get("latest_timestamp") else [],
                }
            )

        if not outcomes:
            improving = trend_analysis.get("improving_metrics") or []
            deteriorating = trend_analysis.get("deteriorating_metrics") or []
            behavioral_status = "improving" if improving else "not_stabilized" if deteriorating else "limited_data"
            outcomes.append(
                {
                    "title": "Behavioral adherence pattern",
                    "category": "behavioral",
                    "status": behavioral_status,
                    "effectiveness_score": 68.0 if improving else 38.0 if deteriorating else 50.0,
                    "narrative": (
                        "Behavioral inputs show recovery-supportive movement."
                        if improving
                        else "Behavioral inputs remain inconsistent and may be limiting stabilization."
                        if deteriorating
                        else "There is limited telemetry to assess behavioral adherence."
                    ),
                    "evidence_ids": [],
                }
            )

        improving_count = sum(1 for item in outcomes if item.get("status") == "improving")
        not_stabilized_count = sum(1 for item in outcomes if item.get("status") == "not_stabilized")
        overall_status = "improving" if improving_count > not_stabilized_count else "watchful" if not_stabilized_count else "limited_data"
        return {
            "overall_status": overall_status,
            "behavioral_adherence": outcomes[0]["status"] if outcomes else "limited_data",
            "interventions": outcomes,
            "headline": (
                "Interventions are showing measurable early response."
                if overall_status == "improving"
                else "Intervention response remains mixed and needs closer review."
                if overall_status == "watchful"
                else "Intervention impact cannot be measured reliably yet."
            ),
            "stabilization_gap_domains": dedupe_texts(
                [item.get("category") for item in outcomes if item.get("status") == "not_stabilized"],
                limit=4,
            ),
        }
