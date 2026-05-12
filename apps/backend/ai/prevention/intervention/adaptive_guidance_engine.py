from __future__ import annotations

from ..utils import safe_dict, safe_list, safe_text


class AdaptiveGuidanceEngine:
    @staticmethod
    def generate(
        monitoring_state: dict,
        prioritized_interventions: list[dict],
        deterioration_projection: dict,
        escalation: dict,
        behavior_analysis: dict,
    ) -> dict:
        signals = safe_list(safe_dict(monitoring_state).get("signals"))
        top_signal = safe_dict(signals[0]) if signals else {}
        top_domain = safe_text(top_signal.get("domain"), "health")
        top_actions = [safe_text(item.get("detail") or item.get("title")) for item in safe_list(prioritized_interventions)[:3]]
        projected_summary = safe_text(safe_dict(deterioration_projection).get("summary"))
        behavior_summary = safe_text(safe_dict(behavior_analysis).get("summary"))

        if top_domain == "recovery":
            headline = "Recovery is asking for earlier support"
            summary = (
                "Your recovery has progressively softened while related strain indicators remain elevated. "
                "Protecting sleep and reducing stacked physiologic load is likely the most useful near-term preventive move."
            )
        elif top_domain == "stress":
            headline = "Stress load is building faster than it is clearing"
            summary = (
                "Stress-related markers are accumulating rather than settling between recovery windows. "
                "Shortening the strain cycle now is more valuable than waiting for a sharper deterioration signal."
            )
        elif top_domain == "cardiovascular":
            headline = "Cardiovascular strain deserves closer watch"
            summary = (
                "Recent cardiovascular drift suggests your system may be carrying more load than usual. "
                "Favoring lighter effort and repeating resting measurements can help confirm whether the pattern is stabilizing."
            )
        else:
            headline = "A preventive adjustment is warranted"
            summary = (
                "Several signals are moving in a less favorable direction at the same time. "
                "A smaller set of timely preventive actions is likely to help more than broad, unfocused changes."
            )

        return {
            "headline": headline,
            "summary": summary,
            "focus_domain": top_domain,
            "actions": [item for item in top_actions if item],
            "follow_up": projected_summary or behavior_summary,
            "escalation_level": safe_text(safe_dict(escalation).get("level"), "monitor"),
        }
