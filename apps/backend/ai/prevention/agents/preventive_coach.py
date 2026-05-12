from __future__ import annotations

from ..utils import safe_dict, safe_list, safe_text


class PreventiveCoach:
    @staticmethod
    def generate(guidance: dict, intervention_plan: dict) -> dict:
        priorities = safe_list(safe_dict(intervention_plan).get("priorities"))
        first_action = safe_dict(priorities[0]) if priorities else {}
        return {
            "message": (
                f"{safe_text(safe_dict(guidance).get('summary'))} Start with: {safe_text(first_action.get('detail') or first_action.get('title'))}"
                if priorities
                else safe_text(safe_dict(guidance).get("summary"))
            ).strip(),
            "focus": safe_text(safe_dict(guidance).get("focus_domain"), "general"),
        }
