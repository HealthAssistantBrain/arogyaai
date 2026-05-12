from __future__ import annotations

from ..utils import safe_dict, safe_list, safe_text


class HealthWatchdog:
    @staticmethod
    def evaluate(monitoring_state: dict, deterioration_projection: dict) -> dict:
        signals = safe_list(safe_dict(monitoring_state).get("signals"))
        top_domains = [safe_text(safe_dict(item).get("domain")) for item in signals[:3] if safe_text(safe_dict(item).get("domain"))]
        return {
            "status": "watchful" if float(safe_dict(monitoring_state).get("overall_risk") or 0.0) >= 45.0 else "stable",
            "top_domains": top_domains,
            "summary": safe_text(safe_dict(deterioration_projection).get("summary")),
        }
