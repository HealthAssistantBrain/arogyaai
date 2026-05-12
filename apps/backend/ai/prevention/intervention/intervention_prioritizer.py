from __future__ import annotations

from ..schemas import InterventionAction
from ..utils import clamp, priority_from_score, safe_dict, safe_list, slugify

ACTION_TEMPLATES: dict[str, dict[str, str]] = {
    "recovery": {
        "title": "Prioritize sleep recovery",
        "detail": "Protect a longer sleep window and reduce sustained strain until recovery markers stop sliding.",
    },
    "stress": {
        "title": "Reduce cumulative stress load",
        "detail": "Lower stacked physiologic stressors, keep effort submaximal, and create more decompression time.",
    },
    "cardiovascular": {
        "title": "Lower short-term cardiovascular strain",
        "detail": "Favor lighter exertion, hydration, and repeat resting measurements while the drift remains elevated.",
    },
    "anomaly": {
        "title": "Recheck recurrent anomalies",
        "detail": "Repeat the abnormal signal and escalate sooner if the same pattern returns across multiple readings.",
    },
    "behavior": {
        "title": "Tighten daily preventive habits",
        "detail": "Use smaller, repeatable sleep and activity routines instead of relying on occasional reset days.",
    },
    "deterioration": {
        "title": "Increase observation frequency",
        "detail": "Track the top risk signals more closely over the next few days while the pattern is still evolving.",
    },
}


class InterventionPrioritizer:
    @staticmethod
    def prioritize(signals: list[dict], impact_estimates: dict[str, dict], adherence: dict) -> list[dict]:
        adherence_score = float(safe_dict(adherence).get("adherence_score") or 0.6)
        blockers = safe_list(safe_dict(adherence).get("blockers"))
        ranked: list[tuple[float, InterventionAction]] = []

        for signal_payload in safe_list(signals):
            signal = safe_dict(signal_payload)
            domain = str(signal.get("domain") or "general")
            template = ACTION_TEMPLATES.get(domain, ACTION_TEMPLATES["deterioration"])
            impact = safe_dict(impact_estimates.get(domain))
            risk_score = float(signal.get("risk_score") or 0.0)
            score = clamp(
                risk_score * 0.52
                + float(signal.get("persistence_days") or 0.0) * 4.5
                + float(signal.get("acceleration") or 0.0) * 24.0
                + float(impact.get("expected_impact") or 0.0) * 0.18
                - len(blockers) * 3.0
            )
            priority = priority_from_score(score)
            action = InterventionAction(
                action_id=f"{slugify(domain)}-preventive-action",
                title=template["title"],
                detail=template["detail"],
                priority=priority,
                domains=[domain],
                timing="today" if priority == "high" else "next_24h",
                expected_impact=float(impact.get("expected_impact") or 0.0),
                adherence_probability=round(adherence_score, 4),
                rationale=[
                    str(signal.get("summary") or ""),
                    f"Projected impact is {float(impact.get('expected_impact') or 0.0):.1f} points.",
                ],
                safety_notes=["Use these recommendations as preventive support, not as a diagnosis."],
                source_signal_ids=[str(signal.get("signal_id") or "")],
                metadata={"recovery_probability": impact.get("recovery_probability")},
            )
            ranked.append((score, action))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [action.model_dump(mode="json") for _, action in ranked[:5]]
