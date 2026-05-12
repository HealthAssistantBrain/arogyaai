from __future__ import annotations


class EscalationForecasting:
    @staticmethod
    def level_for(*, severity: str, direction: str) -> str:
        normalized = str(severity or "low").lower()
        if normalized == "high" and direction in {"deteriorating", "worsening"}:
            return "clinician_review"
        if normalized == "moderate" and direction in {"deteriorating", "unstable", "worsening"}:
            return "monitor_closely"
        return "none"
