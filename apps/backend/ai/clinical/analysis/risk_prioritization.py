from __future__ import annotations

from typing import Any

from ..utils import dedupe_texts, percent, risk_label, safe_float, safe_text


class RiskPrioritizationEngine:
    @staticmethod
    def prioritize_patient(
        context: dict[str, Any],
        trend_analysis: dict[str, Any],
        deterioration_analysis: dict[str, Any],
        intervention_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        patient = context.get("patient") if isinstance(context.get("patient"), dict) else {}
        risk_score = safe_float(patient.get("risk_score"), 0.0) or 0.0
        active_alerts = float(patient.get("active_alerts") or 0.0)
        trend_penalty = float(len(trend_analysis.get("deteriorating_metrics") or [])) * 8.0
        intervention_penalty = 12.0 if intervention_analysis.get("overall_status") == "watchful" else 18.0 if intervention_analysis.get("overall_status") == "limited_data" else 0.0
        aggregate = min(100.0, (risk_score * 0.6) + (active_alerts * 6.0) + trend_penalty + intervention_penalty)
        severity = risk_label(aggregate)

        priorities = [
            {
                "label": "Overall risk trajectory",
                "severity": severity,
                "score": round(aggregate, 1),
                "rationale": f"Composite prioritization reflects current risk at {percent(risk_score, scale_if_fraction=False)}%, alert burden, and longitudinal trend drift.",
                "evidence_ids": dedupe_texts([safe_text(patient.get('prediction_id')), safe_text(patient.get('last_activity'))], limit=3),
            }
        ]
        for trend in (trend_analysis.get("deteriorating_metrics") or [])[:3]:
            priorities.append(
                {
                    "label": trend.get("label") or "Trend",
                    "severity": "high" if trend.get("state") == "deteriorating" else "moderate",
                    "score": 70.0 if trend.get("state") == "deteriorating" else 52.0,
                    "rationale": trend.get("narrative") or "Recent telemetry shift requires review.",
                    "evidence_ids": dedupe_texts([safe_text(trend.get("latest_timestamp"))], limit=2),
                }
            )
        return {
            "aggregate_score": round(aggregate, 1),
            "severity": severity,
            "priorities": priorities,
            "escalation_candidate": bool(
                deterioration_analysis.get("escalation_recommended")
                or severity in {"high", "critical"}
            ),
            "instability_clusters": dedupe_texts(
                trend_analysis.get("dominant_domains") or deterioration_analysis.get("domains") or [],
                limit=4,
            ),
            "recovery_failure_pattern": bool(deterioration_analysis.get("recovery_failure_pattern")),
        }

    @staticmethod
    def prioritize_population(patient_rows: list[dict[str, Any]]) -> dict[str, Any]:
        normalized = [item for item in patient_rows if isinstance(item, dict)]
        ordered = sorted(
            normalized,
            key=lambda item: (
                -(safe_float(item.get("risk_score"), 0.0) or 0.0),
                -(safe_float(item.get("active_alerts"), 0.0) or 0.0),
            ),
        )
        highest_risk = [
            {
                "patient_id": safe_text(item.get("patient_id") or item.get("id")),
                "name": safe_text(item.get("name"), "Patient"),
                "risk_score": percent(item.get("risk_score"), scale_if_fraction=False),
                "triage_level": safe_text(item.get("triage_level"), "UNKNOWN"),
                "active_alerts": int(item.get("active_alerts") or 0),
            }
            for item in ordered[:5]
        ]
        worsening = [
            item
            for item in highest_risk
            if safe_text(item.get("triage_level")).upper() in {"HIGH", "CRITICAL"} or int(item.get("active_alerts") or 0) >= 2
        ]
        clusters = [
            {
                "cluster": "Escalation watchlist",
                "count": len(worsening),
                "description": "Patients with elevated triage level or repeated unresolved alerts.",
            },
            {
                "cluster": "Recovery failure patterns",
                "count": len([item for item in highest_risk if int(item.get("active_alerts") or 0) >= 3]),
                "description": "Users with persistent alert burden despite ongoing monitoring.",
            },
        ]
        recovery_failure = [
            {
                "patient_id": item["patient_id"],
                "name": item["name"],
                "pattern": "Persistent alerts with incomplete recovery signal.",
            }
            for item in highest_risk
            if int(item.get("active_alerts") or 0) >= 3
        ][:4]
        return {
            "highest_risk_users": highest_risk,
            "worsening_physiological_trends": worsening[:5],
            "escalation_candidates": worsening[:5],
            "instability_clusters": clusters,
            "recovery_failure_patterns": recovery_failure,
            "summary": (
                f"{len(worsening)} patients currently look escalation-sensitive across the active clinical queue."
                if worsening
                else "No patients currently meet the highest escalation threshold in the active clinical queue."
            ),
        }
